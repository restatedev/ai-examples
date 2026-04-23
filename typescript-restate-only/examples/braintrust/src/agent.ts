import * as restate from "@restatedev/restate-sdk";
import { tool } from "ai";
import { ModelMessage } from "ai";
import { z } from "zod";
import { braintrustTracingHook } from "./braintrust-hooks";
import * as ai from "ai";
import { openai } from "@ai-sdk/openai";
import { wrapAISDK } from "braintrust";

const schema = restate.serde.schema;

const { generateText } = wrapAISDK(ai);

export const InputMessage = z.object({
  message: z.string().default("What's the weather in San Francisco?"),
});

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
    return { temperature: 23, description: "Sunny" };
  });
}

// AGENT
const run = async (ctx: restate.Context, { message }: { message: string }) => {
  const messages: ModelMessage[] = [
    { role: "system", content: "You are a helpful weather assistant." },
    { role: "user", content: message },
  ];

  while (true) {
    const result = await ctx.run(
      "LLM call",
      async () => {
        const { text, toolCalls, finishReason, response } = await generateText({
          model: openai("gpt-4o"),
          prompt: messages,
          tools,
        });
        return { text, toolCalls, finishReason, messages: response.messages };
      },
      { maxRetryAttempts: 3 },
    );
    messages.push(...result.messages);

    if (result.finishReason !== "tool-calls") return result.text;

    for (const { toolName, toolCallId, input } of result.toolCalls) {
      let output;
      switch (toolName) {
        case "getWeather":
          output = await getWeather(ctx, (input as { city: string }).city);
          break;
        default:
          output = `Tool not found: ${toolName}`;
      }
      messages.push({
        role: "tool",
        content: [
          {
            toolName,
            toolCallId,
            type: "tool-result",
            output: { type: "json", value: output },
          },
        ],
      } as ai.ModelMessage);
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

restate.serve({
  services: [agentService],
  defaultServiceOptions: { hooks: [braintrustTracingHook] },
  port: 9080,
});
