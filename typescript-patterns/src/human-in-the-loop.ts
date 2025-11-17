/**
 * Human-in-the-Loop Pattern
 *
 * Implement resilient human approval steps that suspend execution until feedback is received.
 * Durable promises survive crashes and can be recovered across process restarts.
 */
import * as restate from "@restatedev/restate-sdk";
import { Context } from "@restatedev/restate-sdk";
import { notifyModerator, zodPrompt } from "./utils/utils";
import { generateText, tool } from "ai";
import { openai } from "@ai-sdk/openai";
import z from "zod";
import llmCall from "./utils/llm";

const examplePrompt = "Write a poem about Durable Execution";

// <start_here>
const tools = {
  getHumanReview: tool({
    description: "Request human review if policy violation is uncertain.",
    inputSchema: z.object({}),
  }),
};
async function moderate(ctx: Context, { message }: { message: string }) {
  const { text, toolCalls } = await ctx.run(
    "LLM call",
    async () =>
      // Use your preferred LLM SDK here
      llmCall(
        `You are a content moderation agent. Decide if the content violates policy: ${message}`,
        tools,
      ),
    { maxRetryAttempts: 3 },
  );

  if (toolCalls?.[0]?.toolName === "getHumanReview") {
    // Create a recoverable approval promise
    const approval = ctx.awakeable<string>();
    await ctx.run("Notify moderator", () =>
      notifyModerator(message, approval.id),
    );

    // Suspend until moderator resolves the approval
    // Check the service logs to see how to resolve it over HTTP, e.g.:
    // curl http://localhost:8080/restate/awakeables/sign_.../resolve --json '"approved"'
    return await approval.promise;
  }

  return text;
}
// <end_here>

export default restate.service({
  name: "HumanInTheLoopService",
  handlers: {
    moderate: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      moderate,
    ),
  },
});
