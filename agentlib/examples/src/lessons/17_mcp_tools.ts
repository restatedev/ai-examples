// 17: Give an agent the tools of a remote MCP server.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent} from "@restatedev/agentlib";
import {mcpTools} from "@restatedev/agentlib/mcp";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

const guide = agent({
  model,
  maxSteps: 6,
  instructions: "Answer questions about Restate. Search the Restate docs and be brief.",
});

export const docsGuide = restate.service({
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
        const result = yield* guide.run(question, {tools: docs.tools});
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
  },
});
