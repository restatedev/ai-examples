import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, stepCountIs, tool, wrapLanguageModel } from "ai";
import {
  ClaimInput, ClaimInputSchema,
  InsuranceClaim,
  InsuranceClaimSchema,
} from "./utils/types";
import { eligibilityAgent, fraudCheckAgent } from "./utils/utils";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
const schema = restate.serde.schema;

// <start_here>
const run = async (ctx: restate.Context, claim: ClaimInput) => {
  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  const { text } = await generateText({
    model,
    prompt: `Claim: ${JSON.stringify(claim)}`,
    system:
      "You are a claim approval engine. Analyze the claim and use your tools to decide whether to approve.",
    tools: {
      analyzeEligibility: tool({
        description: "Analyze claim eligibility.",
        inputSchema: InsuranceClaimSchema,
        execute: async (claim: InsuranceClaim) =>
          ctx.serviceClient(eligibilityAgent).run(claim),
      }),
      analyzeFraud: tool({
        description: "Analyze probability of fraud.",
        inputSchema: InsuranceClaimSchema,
        execute: async (claim: InsuranceClaim) =>
          ctx.serviceClient(fraudCheckAgent).run(claim),
      }),
    },
    stopWhen: [stepCountIs(10)],
    providerOptions: { openai: { parallelToolCalls: false } },
  });
  // <end_here>

  return text;
};

const agent = restate.service({
  name: "MultiAgentClaimApproval",
  handlers: {
    run: restate.createServiceHandler({ input: schema(ClaimInputSchema) }, run),
  },
});

restate.serve({ services: [agent, eligibilityAgent, fraudCheckAgent] });
