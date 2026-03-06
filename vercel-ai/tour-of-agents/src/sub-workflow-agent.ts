import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, tool, wrapLanguageModel, Output, stepCountIs } from "ai";
import {
  ClaimPrompt,
  ClaimPromptSchema,
  InsuranceClaim,
  InsuranceClaimSchema,
} from "./utils/types";
import { requestHumanReview } from "./utils/utils";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
const schema = restate.serde.schema;

const run = async (ctx: restate.Context, { prompt }: ClaimPrompt) => {
  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  const { text } = await generateText({
    model,
    system:
      "You are an insurance claim evaluation agent. Use these rules: " +
      "* if the amount is more than 1000, ask for human approval, " +
      "* if the amount is less than 1000, decide by yourself",
    prompt,
    tools: {
      // <start_here>
      humanApproval: tool({
        description: "Ask for human approval for high-value claims.",
        inputSchema: InsuranceClaimSchema,
        execute: async (claim: InsuranceClaim) =>
          ctx.serviceClient(humanApprovalWorfklow).requestApproval(claim),
      }),
      // <end_here>
    },
    stopWhen: [stepCountIs(5)],
    providerOptions: { openai: { parallelToolCalls: false } },
  });
  return text;
};

export const agent = restate.service({
  name: "SubWorkflowClaimApprovalAgent",
  handlers: {
    run: restate.createServiceHandler(
      { input: schema(ClaimPromptSchema) },
      run,
    ),
  },
});

// <start_wf>
export const humanApprovalWorfklow = restate.service({
  name: "HumanApprovalWorkflow",
  handlers: {
    requestApproval: async (ctx: restate.Context, claim: InsuranceClaim) => {
      const approval = ctx.awakeable<boolean>();
      await ctx.run("request-review", () =>
        requestHumanReview(claim, approval.id),
      );
      return approval.promise;
    },
  },
});
// <end_wf>

restate.serve({ services: [agent, humanApprovalWorfklow] });
