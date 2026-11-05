import assert from "node:assert/strict";
import {execFile} from "node:child_process";
import {mkdtemp, mkdir, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {dirname, join} from "node:path";
import {after, before, mock, test} from "node:test";
import {promisify} from "node:util";
import {connect} from "@restatedev/restate-sdk-clients";
import {RestateContainer, RestateTestEnvironment} from "@restatedev/restate-sdk-testcontainers";
import type {Message, Model} from "@restatedev/agentlib";

// The coding lesson against a real Restate server, with Modal replaced by a local directory.
const root = await mkdtemp(join(tmpdir(), "coding-agent-"));
const local = (path: string) => join(root, path.replace(/^\/workspace\/?/, ""));
const calls = {create: 0, terminate: 0};

class SandboxFilesystemNotFoundError extends Error {}
class Sandbox {
  constructor(_client: unknown, sandboxId: string) {
    // The handle must point at the sandbox that connect created.
    assert.equal(sandboxId, "sb-1");
  }
  filesystem = {
    readText: (path: string) =>
      readFile(local(path), "utf8").catch(() => {
        throw new SandboxFilesystemNotFoundError(path);
      }),
    async writeText(content: string, path: string) {
      await mkdir(dirname(local(path)), {recursive: true});
      await writeFile(local(path), content);
    },
  };
  async exec(argv: string[]) {
    const result = promisify(execFile)(argv[0]!, argv.slice(1), {cwd: root}).then(
      ({stdout, stderr}) => ({exitCode: 0, stdout, stderr}),
      (error: {code: number; stdout: string; stderr: string}) => ({
        exitCode: error.code,
        stdout: error.stdout,
        stderr: error.stderr,
      }),
    );
    return {
      stdout: {readText: async () => (await result).stdout},
      stderr: {readText: async () => (await result).stderr},
      wait: async () => (await result).exitCode,
    };
  }
  async terminate() {
    calls.terminate++;
  }
  detach() {}
}
class ModalClient {
  apps = {fromName: async () => ({appId: "app"})};
  images = {fromRegistry: () => ({})};
  sandboxes = {
    async create() {
      calls.create++;
      return {sandboxId: "sb-1"};
    },
  };
}
// mock.module matches the resolved file, so this only replaces the lesson's modal
// while both packages pin the same version (0.10.1).
mock.module("modal", {namedExports: {ModalClient, Sandbox, SandboxFilesystemNotFoundError}});

// Write a script, read it back, run it, and report its output.
const coder: Model = function* (request) {
  const last = request.messages.at(-1) as Message;
  if (last.role === "user") {
    const content = "console.log([2, 3, 5, 7].join(','));\n";
    return {
      type: "tool_calls",
      calls: [{id: "write", name: "writeFile", input: {path: "/workspace/primes.js", content}}],
    };
  }
  assert.equal(last.role, "tool");
  if (last.result.status !== "success") assert.fail(`${last.name} failed`);
  if (last.callId === "write")
    return {
      type: "tool_calls",
      calls: [{id: "read", name: "readFile", input: {path: "/workspace/primes.js"}}],
    };
  if (last.callId === "read")
    return {
      type: "tool_calls",
      calls: [{id: "run", name: "runCommand", input: {command: "node primes.js"}}],
    };
  const {stdout} = last.result.output as {stdout: string};
  return {type: "final", text: stdout.trim()};
};
mock.module("@restatedev/agentlib/openai", {namedExports: {openAIModel: () => coder}});
const {codingAgent} = await import("../src/lessons/11_coding_agent.ts");

let env: RestateTestEnvironment;
before(
  async () => {
    env = await RestateTestEnvironment.start({
      services: [codingAgent],
      container: () => new RestateContainer().alwaysReplay().disableRetries(),
    });
  },
  {timeout: 120000},
);
after(async () => {
  await env?.stop();
  await rm(root, {recursive: true, force: true});
});

void test("the coding agent works in one sandbox and releases it", async () => {
  const result = await connect({url: env.baseUrl()})
    .client(codingAgent)
    .ask({task: "Write primes.js and run it."});
  assert.equal(result, "2,3,5,7");
  // Replayed on every suspension, yet created and released exactly once.
  assert.deepEqual(calls, {create: 1, terminate: 1});
});
