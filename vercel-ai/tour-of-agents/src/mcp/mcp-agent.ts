import {
    experimental_MCPClient as MCPClient,
} from '@ai-sdk/mcp';

import * as restate from "@restatedev/restate-sdk";
import { durableCalls, superJson } from "@restatedev/vercel-ai-middleware";

import {generateText, ModelMessage, stepCountIs, wrapLanguageModel} from "ai";
import { handlers } from "@restatedev/restate-sdk";
import shared = handlers.object.shared;
import {createRestateMCPClient} from "./restate-mcp-client";
import {google} from "@ai-sdk/google";

export default restate.object({
    name: "McpChat",
    handlers: {
        message: async (ctx: restate.ObjectContext, req: { message: string }) => {
            const model = wrapLanguageModel({
                // model: openai('gpt-4o-mini'),
                model: google('gemini-2.5-flash-lite'),
                middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
            });

            const messages =
                (await ctx.get<ModelMessage[]>("messages", superJson)) ?? [];
            messages.push({ role: "user", content: req.message });

            const mcpClient: MCPClient = await createRestateMCPClient(ctx, {
                name: "restate_docs",
                transport: {
                    type: "http",
                    url: "https://docs.restate.dev/mcp",
                },
            });

            const res = await generateText({
                model,
                tools: await mcpClient.tools(),
                system: "You are a helpful assistant. Use the provided tools to answer user queries when appropriate.",
                stopWhen: stepCountIs(5),
                messages
            });

            ctx.set("messages", [...messages, ...res.response.messages], superJson);
            return { answer: res.text };
        },
        getHistory: shared(async (ctx: restate.ObjectSharedContext) =>
            ctx.get<ModelMessage[]>("messages", superJson),
        ),
    },
});
