import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, wrapLanguageModel } from "ai";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
import { convertCurrency, processPayment } from "./utils/utils";
import {
  SequentialClaimRequestSchema,
  SequentialClaimRequest,
} from "./utils/types";
const schema = restate.serde.schema;

// <start_here>
const process = async (ctx: restate.Context, req: SequentialClaimRequest) => {
  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  // Step 1: Parse the claim document (LLM step)
  const { text: parsed } = await generateText({
    model,
    system:
      "Extract the claim amount, currency, category, and description from this document.",
    prompt: req.document,
  });
  const claim = JSON.parse(parsed);

  // Step 2: Analyze the claim (LLM step)
  const { text: analysis } = await generateText({
    model,
    system:
      "You are a claims analyst. Assess whether this claim is valid and determine the approved amount.",
    prompt: `Claim: ${parsed}`,
  });

  // Step 3: Convert currency (regular step)
  const amountUsd = await ctx.run("Convert currency", async () =>
    convertCurrency(claim.amount, claim.currency, "USD"),
  );

  // Step 4: Process reimbursement (regular step)
  const confirmation = await ctx.run("Process payment", async () =>
    processPayment(req.claimId, amountUsd),
  );

  return { analysis, amountUsd, confirmation };
};
// <end_here>

const agent = restate.service({
  name: "ClaimReimbursement",
  handlers: {
    process: restate.createServiceHandler(
      { input: schema(SequentialClaimRequestSchema) },
      process,
    ),
  },
});

restate.serve({ services: [agent] });
