import { generateText, ModelMessage } from "ai";
import { openai } from "@ai-sdk/openai";

const model = openai("gpt-4o");

async function llmCall(
  messages: ModelMessage[],
  userMessage: string,
): Promise<{ text: string }> {
  const response = await generateText({
    model,
    messages: [...messages, { role: "user", content: userMessage }],
  });
  return { text: response.text };
}

export default llmCall;
