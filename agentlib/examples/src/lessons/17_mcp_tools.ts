// 17: Give an agent the tools of a remote MCP server.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent, Conversation} from "@restatedev/agentlib";
import {mcpTools} from "@restatedev/agentlib/mcp";
import {z} from "zod";
import {openai} from "@ai-sdk/openai";
import {aiModel} from "@restatedev/agentlib/provider";

const model = aiModel({model: openai(process.env.AGENT_MODEL ?? "gpt-5.4")});

const guide = agent({
  model,
  maxSteps: 6,
  instructions: "Answer questions about Restate. Search the Restate docs and be brief.",
});

export const docsGuide = restate.object({
  name: "DocsGuide",
  handlers: {
    ask: restate.schemas(
      {
        input: z.object({question: z.string().default("What is a virtual object?")}),
        output: z.string(),
      },
      function* ({question}) {
        // The catalog is fetched once and journaled; each tool call is a journaled step.
        const docs = yield* mcpTools({
          url: "https://docs.restate.dev/mcp",
          namespace: "docs",
          protocol: "stateless",
          deferred: false,
          allow: (name) => name !== "submit_feedback",
        });
        const result = yield* guide.run(question, {
          conversation: new Conversation(),
          tools: docs.tools,
        });
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
  },
  options: {state: {preload: ["conversation/meta", "conversation/summary"]}},
});
