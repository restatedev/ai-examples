import assert from "node:assert/strict";
import { after, before, mock, test } from "node:test";
import { asyncTool, journaledModel, type ModelResponse } from "@restatedev/agentlib";
import { connect } from "@restatedev/restate-sdk-clients";
import { RestateContainer, RestateTestEnvironment } from "@restatedev/restate-sdk-testcontainers";
import { z } from "zod";

// Keep provider traffic out of the replay tests while invoking the real handlers.
let searches = 0;
const search = asyncTool({
  description: "Search fixture documents",
  input: z.object({ query: z.string() }),
  async execute() {
    searches++;
    return { text: "A virtual object has durable state.", url: "https://docs.restate.dev" };
  },
});
mock.module("@restatedev/agentlib/mcp", {
  namedExports: {
    mcpTools: function* (options: { namespace: string; allow: (name: string) => boolean }) {
      assert.equal(options.namespace, "docs");
      assert.equal(options.allow("submit_feedback"), false);
      assert.equal(options.allow("search"), true);
      return { tools: { docs_search: search } };
    },
  },
});

const model = journaledModel(async (request): Promise<ModelResponse> => {
  if (request.instructions?.startsWith("Help the user with refunds")) {
    if ((request.step ?? 1) <= 2) {
      return {
        type: "tool_calls",
        calls: [{
          id: `refund-${request.step}`, name: "refund",
          input: request.step === 1
            ? { handler: "getPolicy", input: {} }
            : { handler: "issueRefund", input: { orderId: "O-99", amountCents: 1250 } },
        }],
      };
    }
    const results = request.messages.filter((message) => message.role === "tool");
    assert.deepEqual(results.map((message) => message.result), [
      { status: "success", output: { refundWindowDays: 30, requiresReceipt: true } },
      { status: "success", output: { refundId: "re_O-99", status: "issued" } },
    ]);
    return { type: "final", text: "Demo refund issued within the 30-day policy." };
  }
  if (request.step === 1) {
    const name = "docs_search";
    assert.ok(request.tools.some((tool) => tool.name === name));
    return {
      type: "tool_calls",
      calls: [{ id: "search", name, input: { query: "virtual objects" } }],
    };
  }
  const result = request.messages.at(-1);
  assert.equal(result?.role, "tool");
  assert.equal(result.result.status, "success");
  return { type: "final", text: "A virtual object has durable state. https://docs.restate.dev" };
});
mock.module("@restatedev/agentlib/openai", { namedExports: { openAIModel: () => model } });
const { refundAgent, refundService } = await import("../src/lessons/10_service_tool.js");
const { docsGuide } = await import("../src/lessons/17_mcp_tools.js");

let env: RestateTestEnvironment;
before(async () => {
  env = await RestateTestEnvironment.start({
    services: [refundAgent, refundService, docsGuide],
    container: () => new RestateContainer().alwaysReplay().disableRetries(),
  });
}, { timeout: 60000 });
after(async () => { await env?.stop(); });

test("service tool dispatches both handlers through durable RPC", async () => {
  const result = await connect({ url: env.baseUrl() }).client(refundAgent).ask({message: "Refund O-99"});
  assert.equal(result, "Demo refund issued within the 30-day policy.");
});

test("MCP handler uses its tools without repeating committed effects", async () => {
  const ingress = connect({ url: env.baseUrl() });
  assert.match(await ingress.client(docsGuide).ask({question: "Explain virtual objects"}), /durable state/);
  assert.equal(searches, 1);
});
