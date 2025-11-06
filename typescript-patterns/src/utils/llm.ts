import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";

async function llmCall(message: string): Promise<string> {
  const response = await generateText({
    model: openai("gpt-4"),
    prompt: `Extract only the numerical values and their associated metrics from the text. 
            Format each as 'metric name: metric' on a new line. Input: ${message}`,
  });
  return response.text;
}

export default llmCall;
