import * as restate from "@restatedev/restate-sdk";
import { ObjectContext } from "@restatedev/restate-sdk";
import llmCall from "./utils/llm";
import { zodPrompt } from "./utils/utils";
import { ModelMessage } from "@ai-sdk/provider-utils";

const examplePrompt = "Write a poem about Durable Execution";

/**
 * Long-lived, Stateful Chat Sessions
 *
 * Maintains conversation state across multiple requests using Restate's persistent memory.
 * Sessions survive failures and can be resumed at any time.
 */
async function onMessage(ctx: ObjectContext, { message }: { message: string }) {
  const messages = (await ctx.get<Array<ModelMessage>>("memory")) ?? [];
  messages.push({ role: "user", content: message });

  const result = await ctx.run("LLM call", async () => llmCall(messages), {
    maxRetryAttempts: 3,
  });

  messages.push({ role: "assistant", content: result });
  ctx.set("memory", messages);

  return result;
}

export default restate.object({
  name: "Chat",
  handlers: {
    message: restate.createObjectHandler(
      { input: zodPrompt(examplePrompt) },
      onMessage,
    ),
  },
});
