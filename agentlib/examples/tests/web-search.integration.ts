import assert from "node:assert/strict";
import {after, before, mock, test} from "node:test";
import {journaledModel, type ModelResponse} from "@restatedev/agentlib";
import {connect} from "@restatedev/restate-sdk-clients";
import {RestateContainer, RestateTestEnvironment} from "@restatedev/restate-sdk-testcontainers";

// Run the real tool, replacing only the external model and Tavily HTTP response.
const model = journaledModel(async (request): Promise<ModelResponse> => {
  assert.ok(!JSON.stringify(request).includes("test-tavily-key"));
  if (request.step === 1) {
    const question = request.messages.find((message) => message.role === "user");
    assert.ok(question && question.role === "user");
    return {type: "tool_calls", calls: [{id: "search", name: "searchWeb", input: {query: question.content}}]};
  }
  const result = request.messages.at(-1);
  assert.equal(result?.role, "tool");
  return {type: "final", text: JSON.stringify(result.result)};
});
mock.module("@restatedev/agentlib/openai", {namedExports: {openAIModel: () => model}});
const {webResearch} = await import("../src/lessons/14_web_search.js");

const attempts = new Map<string, number>();
const originalFetch = globalThis.fetch;
const originalKey = process.env.TAVILY_API_KEY;
let env: RestateTestEnvironment;
before(async () => {
  process.env.TAVILY_API_KEY = "test-tavily-key";
  mock.method(globalThis, "fetch", async (...args: Parameters<typeof fetch>) => {
    const [url, options] = args;
    if (url !== "https://api.tavily.com/search") return originalFetch(...args);
    assert.equal(options?.method, "POST");
    assert.equal(new Headers(options.headers).get("Authorization"), "Bearer test-tavily-key");
    assert.ok(options.signal);
    const {query, max_results, include_raw_content} = JSON.parse(options.body as string);
    assert.equal(max_results, 5);
    assert.equal(include_raw_content, false);
    const count = (attempts.get(query) ?? 0) + 1;
    attempts.set(query, count);
    if (query === "retry" && count < 3) return new Response(null, {status: count === 1 ? 429 : 503});
    if (query === "exhausted") return new Response(null, {status: 503});
    if (query === "unauthorized") return new Response(null, {status: 401});
    if (query === "invalid") return Response.json({results: [{url: "not a URL"}]});
    return Response.json({results: Array.from({length: 7}, (_, i) => ({
      title: `Source ${i}`, url: `https://docs.restate.dev/${i}`, content: "x".repeat(i === 0 ? 5000 : 100),
    }))});
  });
  env = await RestateTestEnvironment.start({
    services: [webResearch],
    container: () => new RestateContainer().alwaysReplay().disableRetries(),
  });
}, {timeout: 60000});
after(async () => {
  await env?.stop();
  mock.restoreAll();
  if (originalKey === undefined) delete process.env.TAVILY_API_KEY;
  else process.env.TAVILY_API_KEY = originalKey;
});

async function search(question: string) {
  return JSON.parse(await connect({url: env.baseUrl()}).client(webResearch).answer({question}));
}

test("web search journals HTTP results and bounds sources and snippets", async () => {
  const result = await search("success");
  assert.equal(result.status, "success");
  assert.equal(result.output.length, 5);
  assert.equal(result.output[0].content.length, 4000);
  assert.equal(result.output[1].content.length, 100);
  assert.equal(result.output[0].url, "https://docs.restate.dev/0");
  assert.equal(attempts.get("success"), 1);
});

test("web search retries rate limits and server errors", async () => {
  assert.equal((await search("retry")).status, "success");
  assert.equal(attempts.get("retry"), 3);
});

for (const [question, expected, count] of [
  ["unauthorized", "Tavily returned HTTP 401", 1],
  ["invalid", "Tavily returned an unexpected response.", 1],
  ["exhausted", "Tavily returned HTTP 503", 3],
] as const) {
  test(`web search reports ${question} to the model`, async () => {
    const result = await search(question);
    assert.equal(result.status, "error");
    assert.equal(result.message, expected);
    assert.equal(attempts.get(question), count);
  });
}

test("web search reports missing credentials without making an HTTP request", async () => {
  delete process.env.TAVILY_API_KEY;
  try {
    const result = await search("missing-key");
    assert.equal(result.status, "error");
    assert.equal(result.message, "Set TAVILY_API_KEY to use web search.");
    assert.equal(attempts.has("missing-key"), false);
  } finally {
    process.env.TAVILY_API_KEY = "test-tavily-key";
  }
});
