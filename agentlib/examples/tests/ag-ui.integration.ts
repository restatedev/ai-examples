// Runs example 18 under the real AG-UI client, which verifies every event
// sequence it receives, against a Restate server.
import assert from "node:assert/strict";
import {createServer, type Server} from "node:http";
import type {AddressInfo} from "node:net";
import {after, before, mock, test} from "node:test";
import {HttpAgent} from "@ag-ui/client";
import {RestateContainer, RestateTestEnvironment} from "@restatedev/restate-sdk-testcontainers";
import type {Model, ModelResponse} from "@restatedev/agentlib";

// Status questions look the order up, highlighting runs the client's tool,
// and anything else cancels the order.
const orders: Model = function* (request): Generator<never, ModelResponse> {
  const last = request.messages.at(-1)!;
  if (last.role === "tool") {
    if (last.result.status !== "success")
      return {type: "final", text: "Order O-7 was left unchanged."};
    const {status} = last.result.output as {status: string};
    return {type: "final", text: `Order O-7 is ${status}.`};
  }
  const text = last.role === "user" ? last.content : "";
  let name = "cancelOrder";
  if (text.includes("status")) name = "lookupOrder";
  else if (text.includes("Highlight")) name = "highlightOrder";
  // Call IDs stay unique across the thread's turns.
  const turn = request.messages.filter((message) => message.role === "user").length;
  return {type: "tool_calls", calls: [{id: `${name}-${turn}`, name, input: {orderId: "O-7"}}]};
};
mock.module("@restatedev/agentlib/provider", {namedExports: {aiModel: () => orders}});
const {agUiThread, agUiHandler} = await import("../src/lessons/18_ag_ui.ts");

let env: RestateTestEnvironment;
let server: Server;
let url: string;
before(
  async () => {
    env = await RestateTestEnvironment.start({
      services: [agUiThread],
      container: () => new RestateContainer().alwaysReplay().disableRetries(),
    });
    server = createServer(agUiHandler(env.baseUrl()));
    await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
    url = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  },
  {timeout: 60000},
);
after(async () => {
  server?.close();
  await env?.stop();
});

function client(threadId: string, text: string) {
  const agent = new HttpAgent({url, threadId});
  agent.addMessage({id: crypto.randomUUID(), role: "user", content: text});
  return agent;
}

void test("a run streams the tool call, its result and the answer", {timeout: 30000}, async () => {
  const agent = client("status", "What is the status of order O-7?");
  const {newMessages} = await agent.runAgent();
  assert.deepEqual(
    agent.messages.map((message) => message.role),
    ["user", "assistant", "tool", "assistant"],
  );
  const [call] = (agent.messages[1] as {toolCalls: {function: {name: string; arguments: string}}[]})
    .toolCalls;
  assert.equal(call!.function.name, "lookupOrder");
  assert.deepEqual(JSON.parse(call!.function.arguments), {orderId: "O-7"});
  // The tool result is JSON, which clients such as CopilotKit parse.
  assert.deepEqual(JSON.parse(agent.messages[2]!.content as string), {
    status: "success",
    output: {orderId: "O-7", status: "shipped"},
  });
  assert.equal(newMessages.at(-1)!.content, "Order O-7 is shipped.");
});

for (const approved of [true, false]) {
  void test(
    `an approval interrupts the run and a resume ${approved ? "approves" : "rejects"} it`,
    {timeout: 30000},
    async () => {
      const agent = client(`cancel-${approved}`, "Cancel order O-7.");
      await agent.runAgent();
      const [interrupt] = agent.pendingInterrupts;
      assert.equal(agent.pendingInterrupts.length, 1);
      assert.equal(interrupt!.toolCallId, "cancelOrder-1");

      // The turn waited in Restate with no stream open; the resume follows it on.
      const {newMessages} = await agent.runAgent({
        resume: [{interruptId: interrupt!.id, status: "resolved", payload: {approved}}],
      });
      assert.equal(agent.pendingInterrupts.length, 0);
      const result = agent.messages.find((message) => message.role === "tool");
      assert.equal(JSON.parse(result!.content as string).status, approved ? "success" : "denied");
      assert.equal(
        newMessages.at(-1)!.content,
        approved ? "Order O-7 is cancelled." : "Order O-7 was left unchanged.",
      );
    },
  );
}

void test("a thread keeps its conversation across runs", {timeout: 30000}, async () => {
  const agent = client("memory", "What is the status of order O-7?");
  await agent.runAgent();
  agent.addMessage({id: crypto.randomUUID(), role: "user", content: "And the status now?"});
  const {newMessages} = await agent.runAgent();
  assert.equal(newMessages.at(-1)!.content, "Order O-7 is shipped.");
  const state = env.stateOf(agUiThread, "memory");
  const messages = (await state.get<{role: string}[]>("messages"))!;
  assert.equal(messages.filter((message) => message.role === "user").length, 2);
});

void test("an answer to an interrupt that is not waiting fails the run", async () => {
  const agent = new HttpAgent({url, threadId: "nothing-pending"});
  const errors: string[] = [];
  await agent.runAgent(
    {resume: [{interruptId: "unknown", status: "resolved", payload: {}}]},
    {
      onRunErrorEvent({event}) {
        errors.push(event.message);
      },
    },
  );
  assert.equal(errors.length, 1);
  assert.match(errors[0]!, /not waiting for an answer/);
});

const highlightOrder = {
  name: "highlightOrder",
  description: "Highlight an order on the page.",
  parameters: {type: "object", properties: {orderId: {type: "string"}}, required: ["orderId"]},
};

void test("a client tool ends the run and the next run answers it", {timeout: 30000}, async () => {
  const agent = client("client-tool", "Highlight order O-7.");
  const first = await agent.runAgent(
    {tools: [highlightOrder]},
    {
      onRunErrorEvent({event}) {
        assert.fail(event.message);
      },
    },
  );
  // The client runs the tool, so the run gives it the call and no result.
  assert.deepEqual(
    first.newMessages.map((message) => message.role),
    ["assistant"],
  );
  const [call] = (first.newMessages[0] as {toolCalls: {id: string; function: {name: string}}[]})
    .toolCalls;
  assert.equal(call!.function.name, "highlightOrder");

  agent.addMessage({
    id: crypto.randomUUID(),
    role: "tool",
    toolCallId: call!.id,
    content: JSON.stringify({status: "highlighted"}),
  });
  const {newMessages} = await agent.runAgent();
  assert.equal(newMessages.at(-1)!.content, "Order O-7 is highlighted.");
  assert.deepEqual(
    agent.messages.map((message) => message.role),
    ["user", "assistant", "tool", "assistant"],
  );
});

void test("a run without a new message gets the conversation", {timeout: 30000}, async () => {
  await client("reconnect", "What is the status of order O-7?").runAgent();
  const fresh = new HttpAgent({url, threadId: "reconnect"});
  await fresh.runAgent();
  assert.deepEqual(
    fresh.messages.map((message) => message.role),
    ["user", "assistant", "tool", "assistant"],
  );
  assert.equal(fresh.messages.at(-1)!.content, "Order O-7 is shipped.");
});

void test("a reconnect shows an approval that is still open", {timeout: 30000}, async () => {
  await client("reconnect-approval", "Cancel order O-7.").runAgent();
  const fresh = new HttpAgent({url, threadId: "reconnect-approval"});
  await fresh.runAgent();
  assert.equal(fresh.messages[0]!.content, "Cancel order O-7.");
  const [interrupt] = fresh.pendingInterrupts;
  assert.equal(interrupt!.toolCallId, "cancelOrder-1");
  const {newMessages} = await fresh.runAgent({
    resume: [{interruptId: interrupt!.id, status: "resolved", payload: {approved: true}}],
  });
  assert.equal(newMessages.at(-1)!.content, "Order O-7 is cancelled.");
});

void test(
  "a retried message follows its turn instead of starting another",
  {timeout: 30000},
  async () => {
    const agent = client("retry", "What is the status of order O-7?");
    const [message] = agent.messages;
    await agent.runAgent();
    const retry = new HttpAgent({url, threadId: "retry"});
    retry.addMessage(message!);
    const {newMessages} = await retry.runAgent();
    assert.equal(newMessages.at(-1)!.content, "Order O-7 is shipped.");
    const messages = (await env.stateOf(agUiThread, "retry").get<{role: string}[]>("messages"))!;
    assert.equal(messages.filter((entry) => entry.role === "user").length, 1);
  },
);
