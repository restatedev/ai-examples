// 20: Fork the agent to check hypotheses in parallel.
//
// A sub-agent from agentTool starts with only its task. A fork from forkAgentTool is
// a copy of the running agent instead: it starts from the conversation up to the
// step that called the tool, so each copy builds on the logs the lead already
// read. Its first request repeats that step's request, which a provider can serve
// from its prompt cache. A fork has the run's tools, policies, and limits. Only
// its reply reaches the lead, and it cannot start forks or sub-agents.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent, forkAgentTool, tool} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

const logs = {
  checkout: "12:01 POST /checkout 502: payments timed out after 30s (41 requests)",
  payments:
    "11:58 deployed payments v2.3.0\n12:00 database connection pool exhausted (10 of 10 in use)",
  inventory: "12:00 GET /stock 200, p99 80ms",
};

const investigator = agent({
  model,
  maxSteps: 8,
  instructions:
    "Investigate production incidents. Read the logs of the affected services first. " +
    "When several causes are plausible, check them in parallel with investigate, one " +
    "hypothesis per call. Then name the most likely cause and its evidence.",
  tools: {
    readLogs: tool({
      description: "Read a service's recent log lines.",
      input: z.object({service: z.enum(["checkout", "payments", "inventory"])}),
      *execute({service}) {
        return logs[service];
      },
    }),
    investigate: forkAgentTool({
      description:
        "Check one hypothesis with a copy of yourself that sees this conversation. " +
        "Call it several times in one step to check hypotheses in parallel.",
    }),
  },
});

export const incidentInvestigation = restate.service({
  name: "IncidentInvestigation",
  handlers: {
    investigate: restate.schemas(
      {
        input: z.object({
          incident: z.string().default("Checkout returns 502 errors since 12:00."),
        }),
        output: z.string(),
      },
      function* ({incident}) {
        const result = yield* investigator.run(incident);
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
  },
});
