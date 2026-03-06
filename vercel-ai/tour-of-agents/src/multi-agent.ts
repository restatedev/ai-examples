import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import {generateText, LanguageModel, stepCountIs, tool, wrapLanguageModel} from "ai";
import {
  ClaimInput,
  ClaimInputSchema,
  InsuranceClaim,
  InsuranceClaimSchema,
} from "./utils/types";
import { eligibilityAgent, fraudCheckAgent } from "./utils/utils";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
const schema = restate.serde.schema;

// <start_here>
async function runEligibilityAgent(model: LanguageModel, claim: InsuranceClaim){
  const { text } = await generateText({
    model,
    system:
        "Decide whether the following claim is eligible for reimbursement." +
        "Respond with eligible if it's a medical claim, and not eligible otherwise.",
    prompt: JSON.stringify(claim),
  });
  return text;
}

async function runFraudAgent(model: LanguageModel, claim: InsuranceClaim){
  const { text } = await generateText({
    model,
    system:
        "Decide whether the claim is fraudulent." +
        "Always respond with low risk, medium risk, or high risk.",
    prompt: JSON.stringify(claim),
  });
  return text;
}

const run = async (ctx: restate.Context, claim: ClaimInput) => {
  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  const { text } = await generateText({
    model,
    prompt: `Claim: ${JSON.stringify(claim)}`,
    system:
      "Analyze the insurance claim and use your tools to decide whether to approve.",
    tools: {
      analyzeEligibility: tool({
        description: "Analyze claim eligibility.",
        inputSchema: InsuranceClaimSchema,
        execute: async (claim: InsuranceClaim) => runEligibilityAgent(model, claim),
      }),
      analyzeFraud: tool({
        description: "Analyze probability of fraud.",
        inputSchema: InsuranceClaimSchema,
        execute: async (claim: InsuranceClaim) => runFraudAgent(model, claim),
      }),
    },
    stopWhen: [stepCountIs(10)],
    providerOptions: { openai: { parallelToolCalls: false } },
  });

  return text;
};
// <end_here>

const agent = restate.service({
  name: "MultiAgentClaimApproval",
  handlers: {
    run: restate.createServiceHandler({ input: schema(ClaimInputSchema) }, run),
  },
});

restate.serve({ services: [agent, eligibilityAgent, fraudCheckAgent] });
