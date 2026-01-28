import * as restate from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";

import { z } from "zod";

import { openai } from "@ai-sdk/openai";
import { generateText, stepCountIs, tool, wrapLanguageModel } from "ai";

import * as mathjs from "mathjs";
import { durableCalls, superJson } from "@restatedev/vercel-ai-middleware";
import { createPubsubClient } from "@restatedev/pubsub-client";

const pubsub = createPubsubClient({
  url: "http://localhost:8080",
  name: "pubsub",
});

const agent = restate.service({
  name: "agent",
  handlers: {
    chat: restate.handlers.handler(
      {
        input: serde.zod(
          z.object({
            prompt: z.string(),
            topic: z
              .string()
              .describe("The pub/sub topic for streaming updates"),
          }),
        ),
        output: serde.zod(z.string()),
      },
      async (ctx: restate.Context, { prompt, topic }) => {
        return await runAgent(ctx, prompt, topic);
      },
    ),
  },
});

async function runAgent(ctx: restate.Context, prompt: string, topic: string) {
  await pubsub.publish(
    topic,
    {
      role: "user",
      content: prompt,
    },
    ctx.rand.uuidv4(),
  );

  const model = wrapLanguageModel({
    model: openai("gpt-4o-2024-08-06"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  const { text: answer } = await generateText({
    model,
    tools: {
      calculate: tool({
        description:
          "A tool for evaluating mathematical expressions. " +
          "Example expressions: " +
          "'1.2 * (2 + 4.5)', '12.7 cm to inch', 'sin(45 deg) ^ 2'.",
        inputSchema: z.object({ expression: z.string() }),
        execute: async ({ expression }) => {
          return await ctx.run(
            `evaluating ${expression}`,
            async () => mathjs.evaluate(expression),
            { serde: superJson },
          );
        },
      }),
    },
    stopWhen: [stepCountIs(10)],
    maxRetries: 0,
    onStepFinish: async (step) => {
      console.log("Step finished:", step);
      step.toolCalls.forEach((toolCall) => {
        pubsub.publish(
          topic,
          {
            role: "assistant",
            content: `Tool call: ${toolCall.toolName}(${JSON.stringify(
              toolCall.input,
            )})`,
          },
          ctx.rand.uuidv4(),
        );
      });
      step.toolResults.forEach((toolResult) => {
        pubsub.publish(
          topic,
          {
            role: "assistant",
            content: `Tool result: ${JSON.stringify(toolResult)}`,
          },
          ctx.rand.uuidv4(),
        );
      });
      if (step.text.length > 0) {
        pubsub.publish(
          topic,
          {
            role: "assistant",
            content: step.text,
          },
          ctx.rand.uuidv4(),
        );
      }
    },
    system:
      "You are a helpful assistant with access to a calculator. " +
      "Use the calculator tool for any math. " +
      "Reason step by step and explain your answer.",
    prompt,
  });

  return answer;
}

export default agent;
export type Agent = typeof agent;
