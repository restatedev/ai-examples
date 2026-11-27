// 02: Give the agent one tool, with validated arguments and a journaled result.
// Retry failed model and tool calls with explicit retry policies.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent, asyncTool} from "@restatedev/agentlib";
import {z} from "zod";
import {openai} from "@ai-sdk/openai";
import {aiModel} from "@restatedev/agentlib/provider";

const model = aiModel({
  model: openai(process.env.AGENT_MODEL ?? "gpt-5.4"),
  // Each model call is a journaled step. Restate retries a call that fails with a
  // transient provider error, such as throttling. When the provider specifies a retry
  // delay, the retry waits that long. A missing API key or a rejected request fails
  // without a retry. Without `retry`, agentlib makes up to 3 attempts.
  retry: {
    maxAttempts: 5, // Includes the initial attempt.
    initialInterval: {milliseconds: 500},
    exponentiationFactor: 2,
    maxInterval: {seconds: 5},
  },
});

const support = agent({
  model,
  instructions: "Use lookupTicket to answer questions about demo tickets.",
  tools: {
    lookupTicket: asyncTool({
      description: "Look up a demo ticket's status.",
      input: z.object({ticketId: z.string()}),
      retry: {
        maxAttempts: 5, // Includes the initial attempt.
        initialInterval: {milliseconds: 250},
        exponentiationFactor: 2,
        maxInterval: {seconds: 5},
        maxDuration: {seconds: 30},
      },
      async execute({ticketId}) {
        // Replace this demo record with an ordinary async API call.
        return {ticketId, status: "open"};
      },
    }),
  },
});

export const ticketLookup = restate.service({
  name: "TicketLookup",
  handlers: {
    ask: restate.schemas(
      {
        input: z.object({message: z.string().default("What is the status of ticket T-42?")}),
        output: z.string(),
      },
      function* ({message}) {
        const result = yield* support.run(message);
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
  },
});
