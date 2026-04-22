import { generateText, ModelMessage } from "ai";
import { openai } from "@ai-sdk/openai";

const model = openai("gpt-4o");

async function llmCall(
  prompt: string | Array<ModelMessage>,
): Promise<{ text: string }> {
  const response = await generateText({ model, prompt });
  return { text: response.text };
}

export default llmCall;
