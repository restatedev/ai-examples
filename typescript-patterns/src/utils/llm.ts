import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";
import { ModelMessage } from "@ai-sdk/provider-utils";

const model = openai("gpt-4");

async function llmCall(
  prompt: string | Array<ModelMessage>,
  tools?: Record<string, any>,
) {
  const response = await generateText({ model, prompt, tools });
  return {
    text: response.text,
    toolCalls: response.toolCalls,
    finishReason: response.finishReason,
    messages: response.response.messages,
  };
}

export default llmCall;
