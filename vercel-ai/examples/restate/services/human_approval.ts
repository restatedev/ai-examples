import * as restate from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";
import { durableCalls , toolErrorAsTerminalError } from "@restatedev/vercel-ai-middleware";

import { z } from "zod";

import { openai } from "@ai-sdk/openai";
import {  generateText, tool, wrapLanguageModel } from "ai";

const LoanRequest = z.object({
  amount: z.number(),
  reason: z.string(),
});

const LoanResponse = z.object({
  response: z.string(),
});

const wf = restate.handlers.workflow

export default restate.workflow({
  name: "human",
  handlers: {
    /**
     * This workflow evaluates a loan request.
     */
    run: wf.workflow(
      {
        input: serde.zod(LoanRequest),
        output: serde.zod(LoanResponse),
      },
      async (ctx: restate.WorkflowContext, { amount, reason }) => {
        return await evaluateLoan(ctx, amount, reason);
      }
    ),

    /**
     * A callback handler for a human approval
     */
    approval: wf.shared(
      {
        input: serde.zod(
          z.object({
            approval: z.union([z.literal("approved"), z.literal("denied")]),
            reason: z.string(),
          })
        ),
        output: serde.zod(z.void()),
      },
      async (ctx: restate.WorkflowSharedContext, approval) => {
        ctx.promise("approval").resolve(approval);
      }
    ),
  },
  options: {
    journalRetention: { days: 1 },
    ...toolErrorAsTerminalError,
  },
});

async function evaluateLoan(ctx: restate.WorkflowContext, amount: number, reason: string) {
 
  const model = wrapLanguageModel({
    model: openai("gpt-4o", { structuredOutputs: true }),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });
  

  const { text: answer } = await generateText({
    model,
    tools: {
      riskAnalysis: tool({
        description:
          "A human loan evaluator. It is able to approve risky loans. It replies with an object " +
          " { approval, reason } where approval is 'approved' or 'denied' and reason is a string explaining the decision." +
          " For example: { approval: 'approved', reason: 'The amount is ok' }" +
          " Or { approval: 'denied', reason: 'The amount is too high' }",
        parameters: z.object({ amount: z.number() }),
        execute: async ({ amount }) => {
          // send some how the request to the human evaluator.
          // A human evaluator will receive a notification with all the relevant details and on their own time (maybe days later)
          // respond with the decision.
          // ctx.run("notify a human", async () => sqs.sendMessage({ ... }))

          // and now we wait for the response
          return ctx.promise("approval");
        },
      }),
    },
    maxSteps: 10,
    maxRetries: 0,
    system:
      "You are loan approval officer, " +
      "You are provided the amount and the reason, and the following are the rules: " +
      "* if the reason is the development of nextjs always approve, " +
      "* if the amount is less than 1000, always approve, " +
      "* if the amount is more than 1000 and the reason is unclear, use the riskAnalysis tool to evaluate it " +
      "* if the riskAnalysis tool has denied but the reason was 'pineapple' approve the loan anyways" +
      "Please provide any intermediate reasoning: " + 
      " for example: I would need to invoke a tool, or the tool responded with $RES now doing $ACTION " + 
      "When you give the final answer, " +
      "Please answer with a single word: 'approved' or 'denied'.",
    prompt: `Please evaluate the following amount: ${amount} for the reason: ${reason}.`,
  });

  return { response : answer};
}