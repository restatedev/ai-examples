/**
 * Long-lived, Stateful Chat Sessions
 *
 * Maintains conversation state across multiple requests using Restate's persistent memory.
 * Sessions survive failures and can be resumed at any time.
 */
import * as restate from "@restatedev/restate-sdk";
import { ObjectContext } from "@restatedev/restate-sdk";
import llmCall from "./utils/llm";
import { zodPrompt } from "./utils/utils";
import { ModelMessage } from "@ai-sdk/provider-utils";

const examplePrompt = "Write a poem about Durable Execution";

// <start_here>
async function message(ctx: ObjectContext, { message }: { message: string }) {
  const messages = (await ctx.get<Array<ModelMessage>>("memory")) ?? [];
  messages.push({ role: "user", content: message });

  // Use your preferred LLM SDK here
  const result = await ctx.run("LLM call", async () => llmCall(messages));

  messages.push({ role: "assistant", content: result.text });
  ctx.set("memory", messages);

  return result.text;
}

export default restate.object({
  name: "Chat",
  handlers: {
    message: restate.createObjectHandler(
      { input: zodPrompt(examplePrompt) },
      message,
    ),
  },
});
// <end_here>
