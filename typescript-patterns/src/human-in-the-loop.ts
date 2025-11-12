import * as restate from "@restatedev/restate-sdk";
import { Context } from "@restatedev/restate-sdk";
import { notifyModerator, zodPrompt } from "./utils/utils";
import { generateText, tool } from "ai";
import { openai } from "@ai-sdk/openai";
import z from "zod";

const examplePrompt = "Write a poem about Durable Execution";

/**
 * Human-in-the-Loop Pattern
 *
 * Implement resilient human approval steps that suspend execution until feedback is received.
 * Durable promises survive crashes and can be recovered across process restarts.
 */
async function moderate(ctx: Context, { message }: { message: string }) {
  const result = await ctx.run(
    "LLM call",
    async () =>
      generateText({
        model: openai("gpt-4o"),
        prompt: `You are a content moderation agent. Decide if the content violates policy: ${message}`,
        tools: {
          getHumanReview: tool({
            name: "getHumanReview",
            description:
              "Request human review if policy violation is uncertain.",
            inputSchema: z.void(),
          }),
        },
      }),
    { maxRetryAttempts: 3 },
  );

  if (
    result.finishReason === "tool-calls" &&
    result.toolCalls?.[0]?.toolName === "getHumanReview"
  ) {
    // Create a recoverable approval promise
    const approval = ctx.awakeable<string>();

    await ctx.run("Notify moderator", () =>
      notifyModerator(message, approval.id),
    );

    // Suspend until moderator resolves the approval
    return await approval.promise;
  }

  return result;
}

export default restate.service({
  name: "HumanInTheLoopService",
  handlers: {
    moderate: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      moderate,
    ),
  },
});
