import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, tool } from "ai";
import { z } from "zod";
import { Context } from "@restatedev/restate-sdk";
import { zodPrompt } from "./utils/utils";

const examplePrompt =
  "I can't log into my account. Keep getting invalid password errors.";

const SPECIALISTS = {
  BillingAgent: "Expert in payments, charges, and refunds",
  AccountAgent: "Expert in login issues and security",
  ProductAgent: "Expert in features and how-to guides",
} as const;

type Specialist = keyof typeof SPECIALISTS;

async function answerQuestion(ctx: Context, question: { message: string }) {
  // 1. First, decide if a specialist is needed
  const specialistTools: Record<string, any> = {};
  Object.entries(SPECIALISTS).forEach(([name, description]) => {
    specialistTools[name] = tool({
      description,
      inputSchema: z.object({}),
    });
  });
  const routingDecision = await ctx.run(
    "pick_specialist",
    async () =>
      generateText({
        model: openai("gpt-4o"),
        system:
          "You are a customer service routing system. Choose the appropriate specialist to handle this question, or respond directly if no specialist is needed.",
        prompt: question.message,
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

  // 4. Call the specialist over HTTP
  return ctx.genericCall<string, string>({
    service: specialist,
    method: "run",
    parameter: question.message,
  });
}

export default restate.service({
  name: "RemoteAgentRouter",
  handlers: {
    answerQuestion: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      answerQuestion,
    ),
  },
});
