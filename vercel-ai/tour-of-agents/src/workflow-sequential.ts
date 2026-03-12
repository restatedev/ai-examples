import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import {generateText, Output, wrapLanguageModel} from "ai";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
import { convertCurrency, processPayment } from "./utils/utils";
import {ClaimData, ClaimPromptSchema} from "./utils/types";
import { Context } from "@restatedev/restate-sdk";
import { z } from "zod";
const schema = restate.serde.schema;

// <start_here>
const process = async (ctx: Context, {prompt}: {prompt: string}) => {
  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  // Step 1: Parse the claim document (LLM step)
  const { output } = await generateText({
    model,
    system:
      "Extract the claim amount, currency, category, and description.",
    prompt,
    output: Output.object({schema: ClaimData})
  });

  // Step 2: Analyze the claim (LLM step)
  const { output: valid } = await generateText({
    model,
    system:
      "You are a claims analyst. Assess whether this claim is valid and determine the approved amount.",
    prompt: `Claim: ${JSON.stringify(output)}`,
    output: Output.object({schema: z.object({valid: z.boolean()})}),
  });

  if (!valid) {
    return { analysis: "Claim is invalid", amountUsd: 0, confirmation: false };
  }

  // Step 3: Convert currency (regular step)
  const amountUsd = await ctx.run("Convert currency", async () =>
    convertCurrency(output.amount, output.currency, "USD"),
  );

  // Step 4: Process reimbursement (regular step)
  const confirmation = await ctx.run("Process payment", async () =>
    processPayment(ctx.rand.uuidv4(), amountUsd),
  );

  return { analysis: "Claim is valid", amountUsd, confirmation };
};
// <end_here>

const agent = restate.service({
  name: "ClaimReimbursement",
  handlers: {
    process: restate.createServiceHandler(
      { input: schema(ClaimPromptSchema) },
      process,
    ),
  },
});

restate.serve({ services: [agent] });
