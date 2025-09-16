import * as restate from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";

import { z } from "zod";

import { openai } from "@ai-sdk/openai";
import {generateText, stepCountIs, tool, wrapLanguageModel} from "ai";
import { publishMessage } from "./pubsub";

import * as mathjs from "mathjs";
import { durableCalls, superJson } from "@restatedev/vercel-ai-middleware";

// the Restate service that is the durable entry point for the
// agent workflow

const tools = restate.service({
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
          })
        ),
        output: serde.zod(z.string()),
        description: "Use tools to solve math problems",
      },
      async (ctx: restate.Context, { prompt, topic }) => {
        return await toolsExample(ctx, prompt, topic);
      }
    ),
  },
});

// https://ai-sdk.dev/docs/foundations/agents#using-maxsteps
async function toolsExample(
  ctx: restate.Context,
  prompt: string,
  topic: string
) {
  publishMessage(ctx, topic, {
    role: "user",
    content: prompt,
    topic,
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
            { serde: superJson }
          );
        },
      }),
    },
    stopWhen: [stepCountIs(10)],
    maxRetries: 0,
    onStepFinish: async (step) => {
      step.toolCalls.forEach((toolCall) => {
        publishMessage(ctx, topic, {
          role: "assistant",
          content: `Tool call: ${toolCall.toolName}(${JSON.stringify(
            toolCall.input
          )})`,
        });
      });
      step.toolResults.forEach((toolResult) => {
        publishMessage(ctx, topic, {
          role: "assistant",
          content: `Tool result: ${JSON.stringify(toolResult)}`,
        });
      });
      if (step.text.length > 0) {
        publishMessage(ctx, topic, {
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

export default tools;
export type Tool = typeof tools;
