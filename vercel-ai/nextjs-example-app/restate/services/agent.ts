import * as restate from "@restatedev/restate-sdk";
import { Context } from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";
import { openai } from "@ai-sdk/openai";
import {generateText, stepCountIs, wrapLanguageModel} from "ai";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
import { createPubsubClient } from "@restatedev/pubsub-client";
import { calculatorTool } from "./tools/calculator";
import { z } from "zod";

export const Prompt = z.object({
  prompt: z.string(),
  topic: z.string().describe("The pub/sub topic for streaming updates"),
});
export type Prompt = z.infer<typeof Prompt>;


// <start_here>
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
    model: openai("gpt-4o"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  const { text: answer } = await generateText({
    model,
    system:
        "You are a helpful assistant with access to a calculator. " +
        "Use the calculator tool for any math. " +
        "Reason step by step and explain your answer.",
    prompt,
    tools: { calculate: calculatorTool(ctx) },
    onStepFinish: async (step) => {
      async function publish(content: string) {
        pubsub.publish(
          topic,
          { role: "assistant", content },
          ctx.rand.uuidv4(),
        );
      }
      step.toolCalls.forEach(({ toolName, input }) => {
        publish(`Tool call: ${toolName}(${JSON.stringify(input)})`);
      });
      step.toolResults.forEach((toolResult) => {
        publish(`Tool result: ${JSON.stringify(toolResult)}`);
      });
      if (step.text.length > 0) {
        publish(step.text);
      }
    },
    stopWhen: [stepCountIs(10)],
  });

  return answer;
}
// <end_here>

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
