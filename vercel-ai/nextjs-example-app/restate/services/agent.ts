import * as restate from "@restatedev/restate-sdk";
import { Context } from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";
import { z } from "zod";
import { openai } from "@ai-sdk/openai";
import { generateText, stepCountIs, tool, wrapLanguageModel } from "ai";
import * as mathjs from "mathjs";
import { durableCalls, superJson } from "@restatedev/vercel-ai-middleware";
import { createPubsubClient } from "@restatedev/pubsub-client";

const Prompt = z.object({
  prompt: z.string(),
  topic: z.string().describe("The pub/sub topic for streaming updates"),
});
type Prompt = z.infer<typeof Prompt>;

const pubsub = createPubsubClient({
  url: "http://localhost:8080",
  name: "pubsub",
});

async function runAgent(ctx: Context, { prompt, topic }: Prompt) {
  await pubsub.publish(
    topic,
    { role: "user", content: prompt },
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
          "Example expressions: '1.2 * (2 + 4.5)', '12.7 cm to inch', 'sin(45 deg) ^ 2'.",
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
    onStepFinish: async (step) => {
      step.toolCalls.forEach((toolCall) => {
        const content = `Tool call: ${toolCall.toolName}(${JSON.stringify(toolCall.input)})`;
          pubsub.publish(
              topic,
              { role: "assistant", content },
              ctx.rand.uuidv4(),
          );
      });
      step.toolResults.forEach((toolResult) => {
        const content = `Tool result: ${JSON.stringify(toolResult)}`;
          pubsub.publish(
              topic,
              { role: "assistant", content },
              ctx.rand.uuidv4(),
          );
      });
      if (step.text.length > 0) {
          pubsub.publish(
              topic,
              { role: "assistant", content: step.text },
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

const agent = restate.service({
  name: "agent",
  handlers: {
    chat: restate.createServiceHandler(
      { input: serde.zod(Prompt), output: serde.zod(z.string()) },
      runAgent,
    ),
  },
});

export default agent;
export type Agent = typeof agent;
