import * as restate from "@restatedev/restate-sdk";
import { durableCalls, superJson } from "@restatedev/vercel-ai-middleware";
import { openai } from "@ai-sdk/openai";
import { generateText, ModelMessage, wrapLanguageModel } from "ai";
import { handlers } from "@restatedev/restate-sdk";
import { ChatMessageSchema } from "./utils/types";
const schema = restate.serde.schema;
import shared = handlers.object.shared;

// <start_here>
const chatAgent = restate.object({
  name: "Chat",
  handlers: {
    message: restate.createObjectHandler(
      { input: schema(ChatMessageSchema) },
      async (ctx: restate.ObjectContext, { message }: { message: string }) => {
        const model = wrapLanguageModel({
          model: openai("gpt-4o"),
          middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
        });

        // Retrieve the state
        const messages =
          (await ctx.get<ModelMessage[]>("messages", superJson)) ?? [];
        messages.push({ role: "user", content: message });

        const res = await generateText({
          model,
          system: "You are a helpful assistant.",
          messages,
        });

        // Update the state
        ctx.set("messages", [...messages, ...res.response.messages], superJson);
        return { answer: res.text };
      },
    ),
    // Shared handler to retrieve the history
    getHistory: shared(async (ctx: restate.ObjectSharedContext) =>
      ctx.get<ModelMessage[]>("messages", superJson),
    ),
  },
});
// <end_here>

restate.serve({ services: [chatAgent] });
