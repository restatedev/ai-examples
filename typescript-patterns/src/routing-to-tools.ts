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
  createTicket,
  queryUserDb,
  SupportTicket,
  zodPrompt,
  zodQuestion,
  toolResult,
  crmService,
} from "./utils/utils";
import { Context } from "@restatedev/restate-sdk";
import llmCall from "./utils/llm";

const examplePrompt = "On which plan am I?";

// <start_here>
// TOOLS
// Define your tools as your AI SDK requires (here Vercel AI SDK)
const tools = {
  queryUserDatabase: tool({
    description: "Get user account and billing info",
    inputSchema: z.object({}),
  }),
  createSupportTicket: tool({
    description: "Create support tickets",
    inputSchema: z.object({
      description: z.string().describe("Detailed description of the issue"),
    }),
  }),
};

// AGENT
async function route(ctx: Context, req: { message: string; userId: string }) {
  const messages: ModelMessage[] = [
    {
      role: "system",
      content:
        "You are a support agent. " +
        "Use the available tools to answer the user's question. " +
        "If you don't know the answer, create a support ticket",
    },
    { role: "user", content: req.message },
  ];

  while (true) {
    // Call the LLM using your favorite AI SDK
    const result = await ctx.run(
      "LLM call",
      async () => llmCall(messages, tools),
      { maxRetryAttempts: 3 },
    );
    messages.push(...result.messages);

    if (result.finishReason !== "tool-calls") return result.text;

    for (const { toolName, toolCallId, input } of result.toolCalls) {
      let output: string;
      // Use ctx.run to ensure durable execution of tool calls
      switch (toolName) {
        case "queryUserDatabase":
          // Example of a local tool
          output = await ctx.run("Query DB", () => queryUserDb(req.userId));
          break;
        case "createSupportTicket":
          // Example of a remote tool/workflow
          output = await ctx
            .serviceClient(crmService)
            .createSupportTicket(input as SupportTicket);
          break;
        default:
          output = `Tool not found: ${toolName}`;
      }
      messages.push(toolResult(toolCallId, toolName, output));
    }
  }
}
// <end_here>

export default restate.service({
  name: "ToolRouter",
  handlers: {
    route: restate.createServiceHandler(
      { input: zodQuestion(examplePrompt) },
      route,
    ),
  },
});
