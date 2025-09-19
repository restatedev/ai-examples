import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import {generateObject, generateText, stepCountIs, tool, wrapLanguageModel} from "ai";
import {
  InsuranceClaim,
  InsuranceClaimSchema,
  fraudTool,
} from "../utils";
import { durableCalls } from "../middleware";

export default restate.service({
  name: "InsuranceClaimWorkflow",
  handlers: {
    run: async (ctx: restate.Context, claim: InsuranceClaim) => {

      await ctx.run("read invoice PDF", async () => {
        await new Promise((r) => {
          setTimeout(() => {
            r(true);
          }, 1650);
        });
        return ""
      })

      const model = wrapLanguageModel({
        model: openai("gpt-4o"),
        middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
      });

      await ctx.serviceClient(claimParserAgent).run(claim)

      await ctx.run("check eligibility", () => {
        // throw new Error("Retrieving policy failed: Insurance Database down...");
        return "eligible";
      })


      // <start_here>
      const { text } = await generateText({
        model,
        prompt: `Claim: ${JSON.stringify(claim)}`,
        system:
          "You are a claim approval engine. Analyze the claim and use your tools to decide whether to approve.",
        tools: {
          analyzeFraud: tool({
            description: "Analyze probability of fraud.",
            inputSchema: InsuranceClaimSchema,
            execute: async (claim: InsuranceClaim) =>
              ctx.serviceClient(fraudTool).run(claim),
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

export const claimParserAgent = restate.service({
  name: "ClaimParserAgent",
  handlers: {
    run: async (ctx: restate.Context, claim: InsuranceClaim) => {

      const model = wrapLanguageModel({
        model: openai("gpt-4o"),
        middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
      });

      const {object} = await generateObject({
        model,
        schema: InsuranceClaimSchema,
        prompt: JSON.stringify(claim)
      })
      return claim;
    },
  },
});