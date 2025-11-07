import * as restate from "@restatedev/restate-sdk";
import { ObjectContext } from "@restatedev/restate-sdk";
import llmCall from "./utils/llm";
import { utils } from "./utils/utils";
import { ModelMessage } from "@ai-sdk/provider-utils";

const example_prompt = "Write a poem about Durable Execution";

/**
 * Long-lived, Stateful Chat Sessions
 *
 * Maintains conversation state across multiple requests using Restate's persistent memory.
 * Sessions survive failures and can be resumed at any time.
 */
async function messageHandler(
  restate: ObjectContext,
  { message }: { message: string },
) {
  const messages = (await restate.get<Array<ModelMessage>>("memory")) ?? [];
  messages.push({ role: "user", content: message });

  const result = await restate.run("LLM call", async () => llmCall(messages));

  messages.push({ role: "assistant", content: result });
  restate.set("memory", messages);

  return result;
}

export default restate.object({
  name: "Chat",
  handlers: {
    message: restate.createObjectHandler(
      { input: utils(example_prompt) },
      messageHandler,
    ),
  },
});
