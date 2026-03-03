import * as restate from "@restatedev/restate-sdk";
import {
  durableCalls,
  createRestateMCPClient,
  RestateMCPClient,
} from "@restatedev/vercel-ai-middleware";
import { generateText, stepCountIs, wrapLanguageModel } from "ai";
import { openai } from "@ai-sdk/openai";
import {McpPrompt, McpPromptSchema} from "./utils/types";
const schema = restate.serde.schema;

const message = async (ctx: restate.Context, { prompt }: McpPrompt) => {
  let mcpClient: RestateMCPClient | undefined;
  try {
    const model = wrapLanguageModel({
      model: openai("gpt-4o-mini"),
      middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
    });

    // Create a Restate MPC client that persists responses from the MCP server
    mcpClient = await createRestateMCPClient(ctx, {
      name: "my-mcp-client",
      transport: {
        type: "http",
        url: "https://docs.restate.dev/mcp",
      },
    });

    const res = await generateText({
      model,
      tools: await mcpClient.tools(),
      system:
        "You are a helpful assistant. Use the provided tools to answer user queries when appropriate.",
      stopWhen: stepCountIs(5),
      prompt,
    });

    return { answer: res.text };
  } finally {
    await mcpClient?.close();
  }
};

const agent = restate.service({
  name: "McpChat",
  handlers: {
    message: restate.createServiceHandler({ input: schema(McpPromptSchema) }, message),
  },
});

restate.serve({ services: [agent] });
