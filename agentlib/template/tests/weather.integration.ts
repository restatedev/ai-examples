import assert from "node:assert/strict";
import { after, before, mock, test } from "node:test";
import { journaledModel, type ModelResponse } from "@restatedev/agentlib";
import { RestateContainer, RestateTestEnvironment } from "@restatedev/restate-sdk-testcontainers";

let modelCalls = 0;
const model = journaledModel(async (request): Promise<ModelResponse> => {
  modelCalls++;
  if (request.step === 1) {
    return {
      type: "tool_calls",
      calls: [{ id: "weather", name: "getWeather", input: { city: "San Francisco" } }],
    };
  }
  const result = request.messages.at(-1);
  assert.equal(result?.role, "tool");
  assert.deepEqual(result.result, {
    status: "success",
    output: {
      city: "San Francisco", temperature: 23, unit: "celsius",
      description: "Sunny and warm", demo: true,
    },
  });
  return { type: "final", text: "Demo weather in San Francisco: 23°C, sunny and warm." };
});
mock.module("@restatedev/agentlib/openai", { namedExports: { openAIModel: () => model } });
const { weatherService } = await import("../src/agent.js");

let env: RestateTestEnvironment;
before(async () => {
  env = await RestateTestEnvironment.start({
    services: [weatherService],
    container: () => new RestateContainer().alwaysReplay().disableRetries(),
  });
}, { timeout: 60000 });
after(async () => { await env?.stop(); });

test("weather tool and model results survive replay", async () => {
  const response = await fetch(`${env.baseUrl()}/agent/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  assert.equal(response.status, 200);
  const reply = await response.json();
  assert.equal(reply, "Demo weather in San Francisco: 23°C, sunny and warm.");
  assert.equal(modelCalls, 2, "completed model calls must not repeat during replay");
});
