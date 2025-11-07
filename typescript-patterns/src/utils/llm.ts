import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";
import { ModelMessage } from "@ai-sdk/provider-utils";

const model = openai("gpt-4");

async function llmCall(prompt: string | Array<ModelMessage>): Promise<string> {
  const response = await generateText({ model, prompt });
  return response.text;
}

export default llmCall;
