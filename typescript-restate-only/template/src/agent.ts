import * as restate from "@restatedev/restate-sdk";
import { tool } from "ai";
import { ModelMessage } from "ai";
import { callLLM, InputMessage, toolResult } from "./utils/utils";
import { z } from "zod";
const schema = restate.serde.schema;

// TOOL DEFINITIONS
const tools = {
  getWeather: tool({
    description: "Get current weather for a city",
    inputSchema: z.object({
      city: z.string().describe("The city to get weather for"),
    }),
  }),
  // add more tools here
};

// TOOL IMPLEMENTATION
async function getWeather(ctx: restate.Context, city: string) {
  return ctx.run(`get weather ${city}`, () => {
    // Simulate calling a remote API
    return { temperature: 23, description: "Sunny, warm" };
  });
}

// AGENT
const run = async (ctx: restate.Context, { message }: { message: string }) => {
  const messages: ModelMessage[] = [
    { role: "system", content: "You are a helpful weather assistant." },
    { role: "user", content: message },
  ];

  // Durable agent loop - Restate journals each step and recovers on failure
  while (true) {
    // 1. LLM call - journaled so it won't re-execute on recovery
    // Use your preferred LLM SDK here
    const result = await ctx.run(
      "LLM call",
      async () => await callLLM(messages, tools),
      { maxRetryAttempts: 3 },
    );
    messages.push(...result.messages);

    // If the LLM returned a final answer, we're done
    if (result.finishReason !== "tool-calls") return result.text;

    // 2. Execute each tool call durably
    for (const { toolName, toolCallId, input } of result.toolCalls) {
      let output;
      switch (toolName) {
        case "getWeather":
          output = await getWeather(ctx, (input as { city: string }).city);
          break;
        // add more tool calls here
        default:
          output = `Tool not found: ${toolName}`;
      }
      messages.push(toolResult(toolCallId, toolName, output));
    }
  }
};

// AGENT SERVICE
const agentService = restate.service({
  name: "agent",
  handlers: {
    run: restate.createServiceHandler({ input: schema(InputMessage) }, run),
  },
});

restate.serve({ services: [agentService], port: 9080 });
