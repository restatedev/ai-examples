import * as restate from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";
import { durableCalls, superJson } from "@restatedev/vercel-ai-middleware";

import { z } from "zod";

import { openai } from "@ai-sdk/openai";
import { generateText, ModelMessage, wrapLanguageModel } from "ai";

interface ChatState {
  messages: ModelMessage[];
}

const handler = restate.handlers.object;

export default restate.object({
  name: "chat",
  handlers: {
    message: handler.exclusive(
      {
        input: serde.zod(
          z.object({
            message: z.string(),
          }),
        ),
        output: serde.zod(
          z.object({
            answer: z.string(),
          }),
        ),
      },
      async (ctx: restate.ObjectContext<ChatState>, { message }) => {
        const model = wrapLanguageModel({
          model: openai("gpt-4o"),
          middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
        });

        const messages = (await ctx.get("messages", superJson)) ?? [];

        messages.push({ role: "user", content: message } as ModelMessage);

        const response = await generateText({
          model,
          maxRetries: 0,
          system: "You are a helpful assistant.",
          messages,
        });

        ctx.set(
          "messages",
          [...messages, ...response.response.messages],
          superJson,
        );
        return { answer: response.text };
      },
    ),
  },
});
