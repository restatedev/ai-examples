import OpenAI from "openai";
import Anthropic from "@anthropic-ai/sdk";

export async function llmCall(
  prompt: string,
  systemPrompt: string = "",
): Promise<string> {
  /**
   * Calls the model with the given prompt and returns the response.
   *
   * @param prompt - The user prompt to send to the model.
   * @param systemPrompt - The system prompt to send to the model. Defaults to "".
   * @returns The response from the language model.
   */

  if (process.env.OPENAI_API_KEY) {
    const client = new OpenAI();
    const response = await client.chat.completions
      .create({
        model: "gpt-4o",
        max_tokens: 4096,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: prompt },
        ],
        temperature: 0.1,
      })
      .asResponse();

    return ((await response.json()) as any).choices[0].message.content;
  } else if (process.env.ANTHROPIC_API_KEY) {
    const client = new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY,
    });

    const response = await client.messages
      .create({
        model: "claude-3-5-sonnet-latest",
        max_tokens: 4096,
        system: systemPrompt,
        messages: [{ role: "user", content: prompt }],
        temperature: 0.1,
      })
      .asResponse();

    return ((await response.json()) as any).choices[0].message.content;
  } else {
    throw new Error(
      "Missing API key: set either the env var OPENAI_API_KEY or ANTHROPIC_API_KEY",
    );
  }
}

export function extractXml(text: string, tag: string): string {
  /**
   * Extracts the content of the specified XML tag from the given text. Used for parsing structured responses
   *
   * @param text - The text containing the XML.
   * @param tag - The XML tag to extract content from.
   * @returns The content of the specified XML tag, or an empty string if the tag is not found.
   */
  const regex = new RegExp(`<${tag}>(.*?)</${tag}>`, "s");
  const match = text.match(regex);
  return match ? match[1] : "";
}
