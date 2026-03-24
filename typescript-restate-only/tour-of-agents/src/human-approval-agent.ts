/**
 * Human-in-the-Loop Pattern
 *
 * Implement resilient human approval steps that suspend execution until feedback is received.
 * Durable promises survive crashes and can be recovered across process restarts.
 */
import * as restate from "@restatedev/restate-sdk";
import { Context } from "@restatedev/restate-sdk";
import { requestClaimReview, zodPrompt } from "./utils/utils";
import { tool } from "ai";
import z from "zod";
import llmCall from "./utils/llm";

const examplePrompt =
  "Process my hospital bill of 2024-10-01 for 3000USD for a broken leg at General Hospital.";

const tools = {
  humanApproval: tool({
    description: "Ask for human approval for high-value claims.",
    inputSchema: z.object({}),
  }),
};

// <start_here>
async function run(ctx: Context, { message }: { message: string }) {
  const prompt =
    "You are an insurance claim evaluation agent. Use these rules: " +
    "* if the amount is more than 1000, ask for human approval, " +
    "* if the amount is less than 1000, decide by yourself. " +
    `Evaluate this claim: ${message}`;
  const { text, toolCalls } = await ctx.run(
    "LLM call",
    // Use your preferred LLM SDK here
    async () => llmCall(prompt, tools),
    { maxRetryAttempts: 3 },
  );

  if (toolCalls?.[0]?.toolName === "humanApproval") {
    // Create a recoverable approval promise
    const approval = ctx.awakeable<boolean>();
    await ctx.run("request-review", () =>
      requestClaimReview(message, approval.id),
    );

    // Suspend until reviewer resolves the approval
    // Check the service logs to see how to resolve it over HTTP, e.g.:
    // curl http://localhost:8080/restate/awakeables/sign_.../resolve --json 'true'
    return approval.promise;
  }

  return text;
}
// <end_here>

const agentService = restate.service({
  name: "HumanClaimApprovalAgent",
  handlers: {
    run: restate.createServiceHandler({ input: zodPrompt(examplePrompt) }, run),
  },
});

restate.serve({ services: [agentService], port: 9080 });
