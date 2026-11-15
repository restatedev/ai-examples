"""Run with RESTATE_SERVER_BIN=/path/to/restate-server uv run python -m unittest discover -s tests -v.

These tests use a real Restate server and kill the real Python worker process.
They reserve localhost ports 8080, 9070, 9071, 5122 and 19080.
"""

import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
from a2a.client.card_resolver import A2ACardResolver
from a2a.client.transports.jsonrpc import JsonRpcTransport
from a2a.types import (
    GetTaskRequest,
    Message,
    Part,
    Role,
    SendMessageRequest,
    TaskState,
)

ROOT = Path(__file__).resolve().parents[1]
SERVER = os.environ.get("RESTATE_SERVER_BIN")


@unittest.skipUnless(SERVER, "Set RESTATE_SERVER_BIN to run the real-server tests")
class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for port in (8080, 9070, 9071, 5122, 19080):
            with socket.socket() as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    sock.bind(("127.0.0.1", port))
                except OSError as error:
                    raise RuntimeError(f"Port {port} must be free") from error
        cls.temp = tempfile.TemporaryDirectory(prefix="a2a-recovery-")
        cls.lab = Path(cls.temp.name)
        cls.server_log = (cls.lab / "server.log").open("w")
        cls.server = subprocess.Popen(
            [
                SERVER,
                "--base-dir",
                str(cls.lab / "data"),
                "--bind-ip",
                "127.0.0.1",
                "--node-name",
                "a2a-test",
                "--default-num-partitions",
                "1",
                "--no-logo",
            ],
            env=dict(os.environ, RESTATE_DISABLE_TELEMETRY="true"),
            stdout=cls.server_log,
            stderr=cls.server_log,
        )
        for _ in range(200):
            try:
                if (
                    httpx.get("http://127.0.0.1:9070/health", timeout=1).status_code
                    == 200
                ):
                    return
            except httpx.HTTPError:
                pass
            if cls.server.poll() is not None:
                raise AssertionError((cls.lab / "server.log").read_text())
            time.sleep(0.1)
        cls.stop(cls.server)
        raise AssertionError("Restate server startup timed out")

    @staticmethod
    def stop(process: subprocess.Popen) -> None:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.stop(cls.server)
        cls.server_log.close()
        evidence = os.environ.get("RESTATE_TEST_EVIDENCE")
        if evidence:
            import shutil

            shutil.copytree(
                cls.lab,
                evidence,
                ignore=shutil.ignore_patterns("data"),
                dirs_exist_ok=True,
            )
        cls.temp.cleanup()

    def start_worker(self) -> subprocess.Popen:
        return subprocess.Popen(
            [sys.executable, str(ROOT / "tests/recovery_worker.py")],
            cwd=ROOT,
            env=dict(os.environ, PYTHONPATH=str(ROOT), PROBE_EVENTS=str(self.events)),
            stdout=self.worker_log,
            stderr=self.worker_log,
        )

    async def wait_ready(self) -> None:
        for _ in range(100):
            try:
                response = await self.http.get("http://127.0.0.1:19080/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            if self.worker.poll() is not None:
                raise AssertionError(self.log_path.read_text())
            await asyncio.sleep(0.1)
        raise AssertionError("Worker startup timed out")

    async def asyncSetUp(self) -> None:
        self.events = self.lab / f"{self._testMethodName}.jsonl"
        self.log_path = self.lab / f"{self._testMethodName}.log"
        self.worker_log = self.log_path.open("w")
        self.http = httpx.AsyncClient(timeout=45, headers={"A2A-Version": "1.0"})
        self.worker = self.start_worker()
        self.addAsyncCleanup(self.cleanup_worker)
        await self.wait_ready()
        registered = await self.http.post(
            "http://127.0.0.1:9070/deployments",
            json={"uri": "http://127.0.0.1:19080/restate/v1", "force": True},
        )
        registered.raise_for_status()
        self.card = await A2ACardResolver(
            self.http, "http://127.0.0.1:19080"
        ).get_agent_card()
        self.url = self.card.supported_interfaces[0].url
        self.client = JsonRpcTransport(
            self.http, self.card, self.url, is_shared_httpx=True
        )

    async def cleanup_worker(self) -> None:
        await asyncio.to_thread(self.stop, self.worker)
        await self.http.aclose()
        self.worker_log.close()

    def request(
        self, text: str, task_id: str = "", context_id: str = ""
    ) -> SendMessageRequest:
        return SendMessageRequest(
            message=Message(
                message_id=str(uuid4()),
                role=Role.ROLE_USER,
                parts=[Part(text=text)],
                task_id=task_id,
                context_id=context_id,
            )
        )

    def records(self) -> list[dict]:
        return (
            [json.loads(line) for line in self.events.read_text().splitlines()]
            if self.events.exists()
            else []
        )

    async def wait_record(self, kind: str) -> dict:
        for _ in range(200):
            for record in self.records():
                if record["kind"] == kind:
                    return record
            await asyncio.sleep(0.05)
        raise AssertionError(f"No {kind} record; {self.log_path.read_text()[-6000:]}")

    async def rpc(
        self, method: str, params: dict, request_id: str | None = None
    ) -> dict:
        result = await self.http.post(
            self.url,
            json={
                "jsonrpc": "2.0",
                "id": request_id or str(uuid4()),
                "method": method,
                "params": params,
            },
        )
        result.raise_for_status()
        return result.json()

    async def test_sdk_roundtrip_and_idempotency(self) -> None:
        request = self.request("hello")
        result = await self.client.send_message(request)
        self.assertEqual(result.task.status.state, TaskState.TASK_STATE_COMPLETED)
        self.assertEqual(result.task.artifacts[0].parts[0].text, "done: hello")
        self.assertEqual(result.task.history[0].task_id, result.task.id)
        duplicate = await self.client.send_message(request)
        self.assertEqual(duplicate, result)
        self.assertEqual(
            [r["stage"] for r in self.records() if r["kind"] == "effect"],
            ["first", "second"],
        )
        fetched = await self.client.get_task(GetTaskRequest(id=result.task.id))
        self.assertEqual(fetched.id, result.task.id)
        self.assertEqual(len(fetched.history), 1)
        no_history = await self.rpc(
            "GetTask", {"id": result.task.id, "historyLength": 0}
        )
        self.assertNotIn("history", no_history["result"])
        self.assertIn(
            "history", (await self.rpc("GetTask", {"id": result.task.id}))["result"]
        )
        canceled = await self.rpc("CancelTask", {"id": result.task.id})
        self.assertEqual(canceled["error"]["code"], -32002)
        continued = await self.rpc(
            "SendMessage",
            {
                "message": {
                    "messageId": str(uuid4()),
                    "taskId": result.task.id,
                    "role": "ROLE_USER",
                    "parts": [{"text": "continue"}],
                }
            },
        )
        self.assertEqual(continued["error"]["code"], -32004)

    async def test_worker_sigkill_recovers_without_repeating_saved_step(self) -> None:
        pending = asyncio.create_task(self.client.send_message(self.request("slow")))
        checkpoint = await self.wait_record("checkpoint")
        old_pid = self.worker.pid
        self.assertEqual(checkpoint["pid"], old_pid)
        self.worker.kill()
        self.assertEqual(self.worker.wait(timeout=5), -signal.SIGKILL)
        self.worker = self.start_worker()
        await self.wait_ready()
        result = await pending
        self.assertEqual(result.task.status.state, TaskState.TASK_STATE_COMPLETED)
        effects = [r for r in self.records() if r["kind"] == "effect"]
        self.assertEqual([r["stage"] for r in effects], ["first", "second"])
        self.assertEqual(effects[0]["pid"], old_pid)
        self.assertEqual(effects[1]["pid"], self.worker.pid)

    async def test_approval_wait_survives_worker_sigkill(self) -> None:
        pending = asyncio.create_task(
            self.client.send_message(self.request("approval"))
        )
        approval = await self.wait_record("approval-checkpoint")
        self.worker.kill()
        self.worker.wait(timeout=5)
        self.worker = self.start_worker()
        await self.wait_ready()
        response = await self.http.post(
            f"http://127.0.0.1:8080/restate/awakeables/{approval['callback_id']}/resolve",
            json=True,
        )
        response.raise_for_status()
        result = await pending
        self.assertEqual(result.task.status.state, TaskState.TASK_STATE_COMPLETED)
        self.assertEqual(
            [r["stage"] for r in self.records() if r["kind"] == "effect"],
            ["first", "second"],
        )
        self.assertEqual(len([r for r in self.records() if r["kind"] == "approval"]), 1)

    async def test_adk_model_response_is_replayed_after_worker_sigkill(self) -> None:
        pending = asyncio.create_task(self.client.send_message(self.request("adk")))
        checkpoint = await self.wait_record("adk-checkpoint")
        self.worker.kill()
        self.worker.wait(timeout=5)
        self.worker = self.start_worker()
        await self.wait_ready()
        result = await pending
        self.assertEqual(result.task.status.state, TaskState.TASK_STATE_COMPLETED)
        self.assertEqual(result.task.artifacts[0].parts[0].text, "local ADK response")
        models = [r for r in self.records() if r["kind"] == "model"]
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["pid"], checkpoint["pid"])
        self.assertNotEqual(models[0]["pid"], self.worker.pid)

    async def test_multi_turn_history(self) -> None:
        first = await self.client.send_message(self.request("need-input"))
        self.assertEqual(first.task.status.state, TaskState.TASK_STATE_INPUT_REQUIRED)
        second = await self.client.send_message(
            self.request("answer", first.task.id, first.task.context_id)
        )
        self.assertEqual(second.task.status.state, TaskState.TASK_STATE_COMPLETED)
        self.assertEqual(second.task.context_id, first.task.context_id)
        self.assertEqual(
            [m.role for m in second.task.history],
            [Role.ROLE_USER, Role.ROLE_AGENT, Role.ROLE_USER],
        )
        self.assertEqual(
            [m.parts[0].text for m in second.task.history],
            ["need-input", "Please provide input", "answer"],
        )

    async def test_nonblocking_send_and_cancel(self) -> None:
        request = self.request("slow")
        request.configuration.return_immediately = True
        result = await self.client.send_message(request)
        self.assertEqual(result.task.status.state, TaskState.TASK_STATE_WORKING)
        canceled = await self.rpc("CancelTask", {"id": result.task.id})
        self.assertEqual(canceled["result"]["status"]["state"], "TASK_STATE_CANCELED")
        fetched = await self.client.get_task(GetTaskRequest(id=result.task.id))
        self.assertEqual(fetched.status.state, TaskState.TASK_STATE_CANCELED)

    async def test_terminal_failure_persists(self) -> None:
        request = self.request("fail")
        task_id = str(
            uuid5(
                NAMESPACE_URL, f"RecoveryProbeTaskObject:{request.message.message_id}"
            )
        )
        result = await self.rpc(
            "SendMessage",
            {
                "message": {
                    "messageId": request.message.message_id,
                    "role": "ROLE_USER",
                    "parts": [{"text": "fail"}],
                }
            },
        )
        self.assertEqual(result["error"]["code"], -32603)
        task = await self.client.get_task(GetTaskRequest(id=task_id))
        self.assertEqual(task.status.state, TaskState.TASK_STATE_FAILED)
        self.assertTrue(task.status.HasField("timestamp"))

    async def test_nonblocking_followup_and_retry(self) -> None:
        first = await self.client.send_message(self.request("need-input"))
        request = self.request("slow", first.task.id, first.task.context_id)
        request.configuration.return_immediately = True
        accepted = await self.client.send_message(request)
        self.assertEqual(
            accepted.task.history[-1].message_id, request.message.message_id
        )
        self.assertEqual(accepted.task.status.state, TaskState.TASK_STATE_WORKING)
        for _ in range(200):
            task = await self.client.get_task(GetTaskRequest(id=first.task.id))
            if task.status.state == TaskState.TASK_STATE_COMPLETED:
                break
            await asyncio.sleep(0.05)
        else:
            self.fail("Follow-up never completed")
        duplicate = await self.client.send_message(request)
        self.assertEqual(duplicate.task, task)
        self.assertEqual(
            [r["stage"] for r in self.records() if r["kind"] == "effect"],
            ["first", "second"],
        )

    async def test_business_conflict_is_failed_not_canceled(self) -> None:
        first = await self.client.send_message(self.request("need-input"))
        reply = await self.rpc(
            "SendMessage",
            {
                "message": {
                    "messageId": str(uuid4()),
                    "taskId": first.task.id,
                    "contextId": first.task.context_id,
                    "role": "ROLE_USER",
                    "parts": [{"text": "conflict"}],
                }
            },
        )
        self.assertEqual(reply["error"]["code"], -32603)
        task = await self.client.get_task(GetTaskRequest(id=first.task.id))
        self.assertEqual(task.status.state, TaskState.TASK_STATE_FAILED)

    async def test_invalid_envelopes_return_error_without_retry(self) -> None:
        invalid = [
            [],
            {
                "jsonrpc": "2.0",
                "id": True,
                "method": "GetTask",
                "params": {"id": "missing"},
            },
        ]
        for request in invalid:
            with self.subTest(request=request):
                reply = await self.http.post(self.url, json=request, timeout=2)
                reply.raise_for_status()
                body = reply.json()
                self.assertEqual(body["error"]["code"], -32600)
                self.assertIsNone(body["id"])

    async def test_validation_and_unsupported_methods(self) -> None:
        cases = [
            ("SendMessage", {}, -32602),
            ("GetTask", {"id": "missing"}, -32001),
            ("GetTask", {"id": "missing", "historyLength": -1}, -32602),
            ("CreateTaskPushNotificationConfig", {}, -32003),
            ("SendStreamingMessage", {}, -32004),
            ("Unknown", {}, -32601),
            ("message/send", {}, -32601),
            (
                "SendMessage",
                {"message": {"messageId": "bad", "role": "ROLE_USER", "parts": [{}]}},
                -32602,
            ),
        ]
        for method, params, code in cases:
            with self.subTest(method=method, params=params):
                self.assertEqual(
                    (await self.rpc(method, params))["error"]["code"], code
                )
