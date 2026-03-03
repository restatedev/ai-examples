import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, stepCountIs, tool, wrapLanguageModel } from "ai";
import { InsuranceClaim, InsuranceClaimSchema } from "./utils/types";
import { eligibilityAgent, fraudCheckAgent } from "./utils/utils";
import { durableCalls } from "@restatedev/vercel-ai-middleware";

const agent = restate.service({
  name: "MultiAgentClaimApproval",
  handlers: {
    run: async (ctx: restate.Context, claim: InsuranceClaim) => {
      const model = wrapLanguageModel({
        model: openai("gpt-4o"),
        middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
      });

      // <start_here>
      const { text } = await generateText({
        model,
        prompt: `Claim: ${JSON.stringify(claim)}`,
        system:
          "You are a claim approval engine. Analyze the claim and use your tools to decide whether to approve.",
        tools: {
          analyzeEligibility: tool({
            description: "Analyze claim eligibility.",
            inputSchema: InsuranceClaimSchema,
            execute: async (claim: InsuranceClaim) => {
              const { text } = await generateText({
                model,
                system:
                  "Decide whether the following claim is eligible for reimbursement." +
                  "Respond with eligible if it's a medical claim, and not eligible otherwise.",
                prompt: JSON.stringify(claim),
              });
              return text;
            },
          }),
          analyzeFraud: tool({
            description: "Analyze probability of fraud.",
            inputSchema: InsuranceClaimSchema,
            execute: async (claim: InsuranceClaim) => {
              const { text } = await generateText({
                model,
                system:
                  "Decide whether the claim is fraudulent." +
                  "Always respond with low risk, medium risk, or high risk.",
                prompt: JSON.stringify(claim),
              });
              return text;
            },
          }),
        },
        stopWhen: [stepCountIs(10)],
        providerOptions: { openai: { parallelToolCalls: false } },
      });
      // <end_here>

      return text;
    },
  },
});

restate.serve({ services: [agent, eligibilityAgent, fraudCheckAgent] });
