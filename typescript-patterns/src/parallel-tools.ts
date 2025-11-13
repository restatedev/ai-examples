/**
 * Parallel Tool Execution
 *
 * Execute multiple tools in parallel with durable results that persist across failures.
 */
import * as restate from "@restatedev/restate-sdk";
import { ModelMessage, tool } from "ai";
import { z } from "zod";
import { Context, RestatePromise } from "@restatedev/restate-sdk";
import { zodPrompt, fetchWeather, toolResult } from "./utils/utils";
import llmCall from "./utils/llm";

const examplePrompt =
  "What is the weather in New York, San Francisco, and Boston?";

// <start_here>
// Define your tools as your AI SDK requires (here Vercel AI SDK)
const tools = {
  get_weather: tool({
    description: "Get the current weather for a location",
    inputSchema: z.object({ city: z.string() }),
  }),
};

async function run(ctx: Context, { message }: { message: string }) {
  const messages: ModelMessage[] = [{ role: "user", content: message }];

  while (true) {
    // Call LLM with durable execution
    const response = await ctx.run(
      "llm-call",
      async () => llmCall(messages, tools),
      { maxRetryAttempts: 3 },
    );
    messages.push(...response.messages);

    if (!response.toolCalls || response.toolCalls.length === 0) {
      return response.text;
    }

    // Run all tool calls in parallel
    // Create parallel promises for all weather requests
    let toolPromises = [];
    for (let { toolCallId, toolName, input } of response.toolCalls) {
      const { city } = input as { city: string };
      const promise = ctx.run(`Get weather ${city}`, () => fetchWeather(city));
      toolPromises.push({ toolCallId, toolName, promise });
    }

    // Wait for all tools to complete in parallel
    await RestatePromise.all(toolPromises.map(({ promise }) => promise));

    // Append all results to messages
    for (const { toolCallId, toolName, promise } of toolPromises) {
      messages.push(toolResult(toolCallId, toolName, await promise));
    }
  }
}
// <end_here>

export default restate.service({
  name: "ParallelToolAgent",
  handlers: {
    run: restate.createServiceHandler({ input: zodPrompt(examplePrompt) }, run),
  },
});
