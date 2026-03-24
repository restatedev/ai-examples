/**
 * LLM Prompt Chaining
 *
 * Build fault-tolerant processing pipelines where each step transforms the previous step's output.
 * If any step fails, Restate automatically resumes from that point.
 *
 * Input → Analysis → Extraction → Summary → Result
 */
import * as restate from "@restatedev/restate-sdk";
import { Context } from "@restatedev/restate-sdk";
import {
  ClaimData,
  convertCurrency,
  processPayment,
  zodPrompt,
} from "./utils/utils";
import { openai } from "@ai-sdk/openai";
import { generateText, Output } from "ai";
import { z } from "zod";

const examplePrompt =
  "Process my hospital bill of 2024-10-01 for 3000USD for a broken leg at General Hospital.";

// <start_here>
async function process(ctx: Context, { message }: { message: string }) {
  // Step 1: Parse the claim document (LLM step)
  const { output } = await ctx.run(
    "Parse claim",
    async () => {
      const { output } = await generateText({
        model: openai("gpt-4o"),
        prompt: `Extract the claim amount, currency, category, and description. Input: ${message}`,
        output: Output.object({ schema: ClaimData }),
      });
      return { output };
    },
    { maxRetryAttempts: 3 },
  );

  // Step 2: Evaluate the claim (LLM step)
  const { valid } = await ctx.run(
    "Evaluate claim",
    async () => {
      const { output: valid } = await generateText({
        model: openai("gpt-4o"),
        system:
          "You are a claims analyst. Assess whether this claim is valid and determine the approved amount.",
        prompt: `Claim: ${JSON.stringify(output)}`,
        output: Output.object({schema: z.object({valid: z.boolean()})}),
      });
      return valid;
    },
    { maxRetryAttempts: 3 },
  );

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
}
// <end_here>

const chainingService = restate.service({
  name: "ClaimReimbursement",
  handlers: {
    process: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      process,
    ),
  },
});

restate.serve({ services: [chainingService], port: 9080 });
