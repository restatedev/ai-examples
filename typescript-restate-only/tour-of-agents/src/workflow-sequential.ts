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

const examplePrompt =
  "Process my hospital bill of 2024-10-01 for 3000USD for a broken leg at General Hospital.";

// <start_here>
async function process(ctx: Context, { message }: { message: string }) {
  // Step 1: Parse the claim document (LLM step)
  const { output } = await ctx.run(
    "Extract metrics",
    async () => {
      const { output } = await generateText({
        model: openai("gpt-4"),
        prompt: `Extract the claim amount, currency, category, and description. Input: ${message}`,
        output: Output.object({ schema: ClaimData }),
      });
      return { output };
    },
    { maxRetryAttempts: 3 },
  );

  // Step 2: Analyze the claim (LLM step)
  const { text: analysis } = await ctx.run(
    "Sort metrics",
    async () => {
      const { text } = await generateText({
        model: openai("gpt-4"),
        prompt: `Assess whether this claim is valid and determine the approved amount: ${output}`,
      });
      return { text };
    },
    { maxRetryAttempts: 3 },
  );

  // Step 3: Convert currency (regular step)
  const amountUsd = await ctx.run("Convert currency", async () =>
    convertCurrency(output.amount, output.currency, "USD"),
  );

  // Step 4: Process reimbursement (regular step)
  const confirmation = await ctx.run("Process payment", async () =>
    processPayment(ctx.rand.uuidv4(), amountUsd),
  );

  return { analysis, amountUsd, confirmation };
}
// <end_here>

const chainingService = restate.service({
  name: "CallChainingService",
  handlers: {
    process: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      process,
    ),
  },
});

restate.serve({ services: [chainingService], port: 9080 });
