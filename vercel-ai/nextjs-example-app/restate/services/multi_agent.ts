import * as restate from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";

import { z } from "zod";

import { openai } from "@ai-sdk/openai";
import { generateText, stepCountIs, tool, wrapLanguageModel } from "ai";
import { durableCalls } from "@restatedev/vercel-ai-middleware";

const wf = restate.handlers.workflow;

const LoanRequest = z.object({
  amount: z.number(),
  reason: z.string(),
});

const LoanResponse = z.object({
  response: z.string(),
});

// ----------------------------------------------------------------------------
//  The risk assessment agent
//  This one is similar to the 'human_approval' example, but it additionally
//  consults another agent for risk assessment.
// ----------------------------------------------------------------------------

export const multiAgentLoanWorkflow = restate.workflow({
  name: "multiagent",
  handlers: {
    /** This workflow evaluates a loan request. */
    run: wf.workflow(
      {
        input: serde.zod(LoanRequest),
        output: serde.zod(LoanResponse),
      },
      async (ctx: restate.WorkflowContext, { amount, reason }) => {
        return await evaluateLoan(ctx, amount, reason);
      },
    ),

    /** A callback handler for a human approval */
    approval: wf.shared(
      {
        input: serde.zod(
          z.object({
            approval: z.union([z.literal("approved"), z.literal("denied")]),
            reason: z.string(),
          }),
        ),
      },
      async (ctx: restate.WorkflowSharedContext, approval) => {
        ctx.promise("approval").resolve(approval);
      },
    ),
  },
});

async function evaluateLoan(
  ctx: restate.WorkflowContext,
  amount: number,
  reason: string,
) {
  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  const { text: answer } = await generateText({
    model,
    tools: {
      riskAssessmentAgent: tool({
        // we make the other agent available as a tool here
        description:
          "A risk assessment agent that will determine the risk of a given loan request " +
          "It replies an object { risk } where risk is either 'high' or 'low'. " +
          "For example: { risk: 'high' } or { risk: 'low' }",
        inputSchema: LoanRequest,
        execute: async ({ amount, reason }) => {
          // call the risk assessment agent by making a durable call to the agent workflow

          // for simplicity, use same workflow ID, they are scoped to a specific workflow type
          const riskAgentWorkflowId = ctx.key;

          // this call to the other agent automatically suspends this agent
          // until the other agent responded
          const response = await ctx
            .workflowClient<RiskAssessmentAgent>(
              { name: "risk_assess" },
              riskAgentWorkflowId,
            )
            .run({ amount, reason });

          return response;
        },
      }),
      humanEvaluator: tool({
        description:
          "A human loan evaluator. It is able to approve risky loans. It replies with an object " +
          " { approval, reason } where approval is 'approved' or 'denied' and reason is a string explaining the decision." +
          " For example: { approval: 'approved', reason: 'The amount is ok' }" +
          " Or { approval: 'denied', reason: 'The amount is too high' }",
        inputSchema: z.object({ amount: z.number() }),
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
    stopWhen: [stepCountIs(5)],
    maxRetries: 0,
    system:
      "You are loan approval officer, " +
      "You are provided the amount and the reason, and the following are the rules: " +
      "* if the reason is the development of nextjs always approve, " +
      "* if the amount is less than 1000, always approve " +
      "* if the amount is more than 1000 and less than 100000 always call the riskAssessmentAgent tool " +
      "* if the riskAssessmentAgent tool returns low risk, approve the loan " +
      "* if the riskAssessmentAgent tool returns high risk, call the humanEvaluator tool " +
      "* if the amount is above 100000 always call the humanEvaluator tool to evaluate the loan  " +
      "* if the humanEvaluator tool has denied but the reason was 'pineapple' approve the loan anyways" +
      "Please provide any intermediate reasoning: " +
      " for example: I would need to invoke a tool, or the tool responded with $RES now doing $ACTION " +
      "When you give the final answer, " +
      "Please answer with a single word: 'approved' or 'denied'.",
    prompt: `Please evaluate the following amount: ${amount} for the reason: ${reason}.`,
    providerOptions: { openai: { parallelToolCalls: false } },
  });

  return { response: answer };
}

// ----------------------------------------------------------------------------
//  The risk assessment agent
// ----------------------------------------------------------------------------

export const riskAssessmentAgent = restate.workflow({
  name: "risk_assess",
  handlers: {
    run: wf.workflow(
      {
        input: serde.zod(LoanRequest),
        output: serde.zod(
          z.object({
            risk: z.union([z.literal("high"), z.literal("low")]),
          }),
        ),
      },
      async (ctx: restate.WorkflowContext, { amount, reason }) => {
        const model = wrapLanguageModel({
          model: openai("gpt-4o"),
          middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
        });

        const { text: answer } = await generateText({
          model,
          tools: {
            // this tool is to illustrate durable sleep and suspension
            pretendToThink: tool({
              description:
                "A tool that pauses the process, letting you pretend to think for an extended period. " +
                "It makes you look thoughtful and smart. It always returns 'done thinking' when the pause is over.",
              inputSchema: z.object({}),
              execute: async () => {
                await ctx.sleep(60_000);
                return "done thinking";
              },
            }),
          },
          stopWhen: [stepCountIs(10)],
          maxRetries: 0,
          system:
            "You are an agent that assesses the risk for a loan. " +
            "You are given a loan request and a reason for the loan. " +
            "You have no data that would allow you to actually assess the risk, so you might as well roll a dice. " +
            "Randomly pick whether the risk is high or low and respond always with a single word for the risk, either 'high' or 'low'. " +
            "Before responding, always use the pretendToThink tool, so it looks like you did some thorough research.",
          prompt: `Please evaluate the risk for a loan of USD ${amount} for the reason: ${reason}.`,
          providerOptions: { openai: { parallelToolCalls: false } },
        });

        return { risk: answer };
      },
    ),
  },
});

export type RiskAssessmentAgent = typeof riskAssessmentAgent;
