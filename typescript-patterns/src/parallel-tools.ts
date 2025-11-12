import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, ModelMessage, tool } from "ai";
import { z } from "zod";
import { Context } from "@restatedev/restate-sdk";
import { zodPrompt, fetchWeather } from "./utils/utils";

const examplePrompt = "What is the weather in New York, San Francisco, and Boston?";

async function run(ctx: Context, prompt: { message: string }): Promise<string> {
  const messages: ModelMessage[] = [
    { role: "user", content: prompt.message }
  ];

  while (true) {
    // Call LLM with durable execution
    const response = await ctx.run(
      "llm-call",
      async () => generateText({
        model: openai("gpt-4o"),
        messages,
        tools: {
          get_weather: tool({
            description: "Get the current weather for a location",
            inputSchema: z.object({
              location: z.string()
            }),
          }),
        },
      }),
      { maxRetryAttempts: 3 }
    );

    messages.push(...response.response.messages);

    if (!response.toolCalls || response.toolCalls.length === 0) {
      return response.text;
    }

    // Run all tool calls in parallel
    // Create parallel promises for all weather requests
    let toolPromises = [];
    for (let toolCall of response.toolCalls) {
        const {location} = toolCall.input as { location: string };
        const weather = await ctx.run(
            `Get weather ${location}`,
            () => fetchWeather(location)
        );
        toolPromises.push({
            toolCallId: toolCall.toolCallId,
            toolName: toolCall.toolName,
            result: weather
        });
    }

    // Wait for all tools to complete in parallel
    const toolResults = await Promise.all(toolPromises);

    // Append all results to messages
    for (const { toolCallId, toolName, result } of toolResults) {
      messages.push({
        role: "tool",
        content: [{
          toolCallId,
          toolName,
          type: "tool-result",
          output: { type: "json", value: result },
        }],
      });
    }
  }
}

export default restate.service({
  name: "ParallelToolAgent",
  handlers: {
    run: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      run
    ),
  },
});