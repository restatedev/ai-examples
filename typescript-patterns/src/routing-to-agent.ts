/**
 * Agent Routing
 *
 * Route customer questions to specialized AI agents based on their content.
 * Each routing decision is durable and can be retried if it fails.
 *
 * Flow: Customer Question → Classifier → Specialized Agent → Response
 */
import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, tool } from "ai";
import { z } from "zod";
import { Context } from "@restatedev/restate-sdk";
import { zodPrompt } from "./utils/utils";

const examplePrompt =
  "I can't log into my account. Keep getting invalid password errors.";

const SPECIALISTS = {
  billing: {
    description: "Expert in payments, charges, and refunds",
    system:
      "You are a billing support agent specializing in payments, charges, and refunds.",
  },
  account: {
    description: "Expert in login issues and security",
    system:
      "You are an account support agent specializing in login issues and security.",
  },
  product: {
    description: "Expert in features and how-to guides",
    system:
      "You are a product support agent specializing in features and how-to guides.",
  },
} as const;

type Specialist = keyof typeof SPECIALISTS;

// <start_here>
async function answerQuestion(ctx: Context, { message }: { message: string }) {
  const specialistTools: Record<string, any> = {};
  Object.entries(SPECIALISTS).forEach(([name, { description }]) => {
    specialistTools[name] = tool({
      description,
      inputSchema: z.object({}),
    });
  });

  // 1. First, decide if a specialist is needed
  const routingDecision = await ctx.run(
    "pick_specialist",
    async () =>
      generateText({
        model: openai("gpt-4o"),
        prompt: message,
        tools: specialistTools,
      }),
    { maxRetryAttempts: 3 },
  );

  // 2. No specialist needed? Give a general answer
  if (!routingDecision.toolCalls || routingDecision.toolCalls.length === 0) {
    return routingDecision.text;
  }

  // 3. Get the specialist's name
  const specialist = routingDecision.toolCalls[0].toolName as Specialist;

  // 4. Ask the specialist to answer
  const answer = await ctx.run(
    `ask_${specialist}`,
    async () =>
      generateText({
        model: openai("gpt-4o"),
        system: SPECIALISTS[specialist].system,
        prompt: message,
      }),
    { maxRetryAttempts: 3 },
  );

  return answer.text;
}
// <end_here>

export default restate.service({
  name: "AgentRouter",
  handlers: {
    answerQuestion: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      answerQuestion,
    ),
  },
});
