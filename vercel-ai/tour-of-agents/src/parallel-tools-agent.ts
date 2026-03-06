import * as restate from "@restatedev/restate-sdk";
import { RestatePromise } from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, tool, wrapLanguageModel, stepCountIs } from "ai";
import {
  ClaimInput,
  ClaimInputSchema,
  InsuranceClaim,
  InsuranceClaimSchema,
} from "./utils/types";
import {
  compareToStandardRates,
  checkEligibility,
  checkFraud,
} from "./utils/utils";
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
    prompt: `Analyze the claim ${JSON.stringify(claim)}.
        Use your tools to calculate key metrics and decide whether to approve.`,
    tools: {
      calculateMetrics: tool({
        description: "Calculate claim metrics.",
        inputSchema: InsuranceClaimSchema,
        execute: async (claim: InsuranceClaim) => {
          // Execute each calculation as a parallel durable step
          return RestatePromise.all([
            ctx.run("eligibility", () => checkEligibility(claim)),
            ctx.run("cost", () => compareToStandardRates(claim)),
            ctx.run("fraud", () => checkFraud(claim)),
          ]);
        },
      }),
    },
    stopWhen: [stepCountIs(10)],
    providerOptions: { openai: { parallelToolCalls: false } },
  });
  return text;
};
// <end_here>

const agent = restate.service({
  name: "ParallelToolClaimAgent",
  handlers: {
    run: restate.createServiceHandler({ input: schema(ClaimInputSchema) }, run),
  },
});

restate.serve({ services: [agent] });
