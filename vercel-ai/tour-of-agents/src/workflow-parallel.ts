import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, wrapLanguageModel } from "ai";
import {ClaimInput, ClaimInputSchema, ClaimPromptSchema} from "./utils/types";
import {
  eligibilityAgent,
  fraudCheckAgent,
  rateComparisonAgent,
} from "./utils/utils";
import { RestatePromise } from "@restatedev/restate-sdk";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
const schema = restate.serde.schema;

const run = async (ctx: restate.Context, claim: ClaimInput) => {
  const [eligibility, rateComparison, fraudCheck] =
    await RestatePromise.all([
      ctx.serviceClient(eligibilityAgent).run(claim),
      ctx.serviceClient(rateComparisonAgent).run(claim),
      ctx.serviceClient(fraudCheckAgent).run(claim),
    ]);

  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  const { text } = await generateText({
    model,
    system: "You are a claim decision engine.",
    prompt: `Decide about claim ${JSON.stringify(claim)}.
        Base your decision on the following analyses:
        Eligibility: ${eligibility}, Cost: ${rateComparison} Fraud: ${fraudCheck}`,
  });
  return text;
};

const agent = restate.service({
  name: "ParallelAgentClaimApproval",
  handlers: {
    run: restate.createServiceHandler({ input: schema(ClaimInputSchema) }, run),
  },
});

restate.serve({
  services: [agent, eligibilityAgent, rateComparisonAgent, fraudCheckAgent],
});
