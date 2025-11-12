import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, ModelMessage, tool } from "ai";
import { z } from "zod";
import {
  fetchServiceStatus,
  createSupportTicket,
  queryUserDb,
  SupportTicket,
} from "./utils/utils";

interface Question {
  userId: string;
  message: string;
}

export default restate.service({
  name: "ToolRouter",
  handlers: {
    route: async (ctx: restate.Context, question: Question) => {
      const messages: ModelMessage[] = [
        { role: "user", content: question.message },
      ];

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
                  queryUserDb(question.userId),
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
    },
  },
});
