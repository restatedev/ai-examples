/**
 * Tool Routing
 *
 * Route requests to tools based on LLM instructions.
 * Agent loop continues calling tools until a final answer is returned.
 *
 * Flow: User Request → LLM → Tool Selection → Tool Execution → Response
 */
import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, ModelMessage, tool } from "ai";
import { z } from "zod";
import {
    fetchServiceStatus,
    createSupportTicket,
    queryUserDb,
    SupportTicket, zodPrompt, zodQuestion,
} from "./utils/utils";
import { Context } from "@restatedev/restate-sdk";

const examplePrompt = "My API calls are failing, what's wrong with my account?"

async function route(ctx: Context, { message, userId }: { message: string, userId: string }) {
  const messages: ModelMessage[] = [{ role: "user", content: message }];

  while (true) {
    const result = await ctx.run(
      "LLM call",
      async () =>
        generateText({
          model: openai("gpt-4o"),
          messages,
          tools: {
            fetchServiceStatus: tool({
              description: "Check service status and outages",
              inputSchema: z.void(),
            }),
            queryUserDatabase: tool({
              description: "Get user account and billing info",
              inputSchema: z.void(),
            }),
            createSupportTicket: tool({
              description: "Create support tickets",
              inputSchema: z.object({
                user_id: z.string().describe("User ID creating the ticket"),
                description: z
                  .string()
                  .describe("Detailed description of the issue"),
              }),
            }),
          },
        }),
      { maxRetryAttempts: 3 },
    );

    messages.push(...result.response.messages);

    if (result.finishReason === "tool-calls") {
      for (const toolCall of result.toolCalls) {
        let toolOutput: string;

        switch (toolCall.toolName) {
          case "queryUserDatabase":
            toolOutput = await ctx.run("query-user-db", () =>
              queryUserDb(userId),
            );
            break;
          case "fetchServiceStatus":
            toolOutput = await ctx.run("fetch-service-status", () =>
              fetchServiceStatus(),
            );
            break;
          case "createSupportTicket":
            toolOutput = await ctx.run("create-support-ticket", () =>
              createSupportTicket(toolCall.input as SupportTicket),
            );
            break;
          default:
            toolOutput = `Tool not found: ${toolCall.toolName}`;
        }

        messages.push({
          role: "tool",
          content: [
            {
              toolName: toolCall.toolName,
              toolCallId: toolCall.toolCallId,
              type: "tool-result",
              output: { type: "json", value: toolOutput },
            },
          ],
        });
      }
    } else {
      return result.text;
    }
  }
}

export default restate.service({
  name: "ToolRouter",
  handlers: {
      route: restate.createServiceHandler(
          { input: zodQuestion(examplePrompt) },
          route,
      ),
  },
});
