import { generateText, ModelMessage } from "ai";
import { openai } from "@ai-sdk/openai";
import { z } from "zod";

export const InputMessage = z.object({
  message: z.string().default("What's the weather in San Francisco?"),
});

export async function callLLM(prompt: ModelMessage[], tools?: Record<string, any>) {
  const response = await generateText({
    model: openai("gpt-4o"),
    prompt,
    tools,
  });
  return {
    text: response.text,
    toolCalls: response.toolCalls,
    finishReason: response.finishReason,
    messages: response.response.messages,
  };
}

export function toolResult(toolCallId: string, toolName: string, output: any) {
  return {
    role: "tool",
    content: [
      {
        toolName,
        toolCallId,
        type: "tool-result",
        output: { type: "json", value: output },
      },
    ],
  } as ModelMessage;
}
