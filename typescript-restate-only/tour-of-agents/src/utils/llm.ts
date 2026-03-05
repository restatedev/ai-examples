import { generateText, TypedToolCall } from "ai";
import { openai } from "@ai-sdk/openai";
import { ModelMessage } from "@ai-sdk/provider-utils";

const model = openai("gpt-4");

async function llmCall(
  prompt: string | Array<ModelMessage>,
  tools?: Record<string, any>,
): Promise<{
  text: string;
  toolCalls: Array<TypedToolCall<Record<string, any>>>;
  finishReason:
    | "stop"
    | "length"
    | "content-filter"
    | "tool-calls"
    | "error"
    | "other"
    | "unknown";
  messages: Array<ModelMessage>;
}> {
  const response = await generateText({ model, prompt, tools });
  return {
    text: response.text,
    toolCalls: response.toolCalls,
    finishReason: response.finishReason,
    messages: response.response.messages,
  };
}

export default llmCall;
