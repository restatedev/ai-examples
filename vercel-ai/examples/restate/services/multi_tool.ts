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
  name: "pubsub", // <-- same as your pubsub virtual object above.
});

// the Restate service that is the durable entry point for the
// agent workflow

const multiToolAgent = restate.service({
  name: "tools",
  handlers: {
    message: restate.handlers.handler(
      {
        input: serde.zod(
          z.object({
            prompt: z.string(),
            topic: z
              .string()
              .default("channel")
              .describe("The topic to publish intermediate steps to"),
          }),
        ),
        output: serde.zod(z.string()),
        description: "Use tools to solve math problems",
      },
      async (ctx: restate.Context, { prompt, topic }) => {
        return await toolsExample(ctx, prompt, topic);
      },
    ),
  },
});

// https://ai-sdk.dev/docs/foundations/agents#using-maxsteps
async function toolsExample(
  ctx: restate.Context,
  prompt: string,
  topic: string,
) {
  await pubsub.publish(topic, {
    role: "user",
    content: prompt
  });

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
          //
          // use the restate API over here to store function calls into
          // the durable log
          //
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
      step.toolCalls.forEach((toolCall) => {
        pubsub.publish(topic, {
          role: "assistant",
          content: `Tool call: ${toolCall.toolName}(${JSON.stringify(
              toolCall.input,
          )})`,
        });
      });
      step.toolResults.forEach((toolResult) => {
        pubsub.publish(topic, {
          role: "assistant",
          content: `Tool result: ${JSON.stringify(toolResult)}`,
        });
      });
      if (step.text.length > 0) {
        pubsub.publish(topic, {
          role: "assistant",
          content: step.text,
        });
      }
    },
    system:
      "You are solving math problems. " +
      "Reason step by step. " +
      "Use the calculator when necessary. " +
      "When you give the final answer, " +
      "provide an explanation for how you arrived at it.",
    prompt,
  });

  return `Answer: ${answer}`;
}

export default multiToolAgent;
export type MultiToolAgent = typeof multiToolAgent;
