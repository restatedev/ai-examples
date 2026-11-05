// 07: Race two agents and cancel the unfinished work after the first success.
// Reimplements restatedev/ai-examples' competitive racing with embedded operations.
import {TerminalError} from "@restatedev/restate-sdk";
import * as restate from "@restatedev/restate-sdk-gen";
import {agent} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

const candidates = {
  quick: agent({
    name: "quick",
    model,
    maxSteps: 2,
    instructions: "Quick answer. Give a concise, direct answer to the question.",
  }),
  thorough: agent({
    name: "thorough",
    model,
    maxSteps: 2,
    instructions:
      "Thorough answer. Check assumptions and edge cases, then give a practical answer.",
  }),
};

type Candidate = (typeof candidates)[keyof typeof candidates];

function* answerWith(name: string, candidate: Candidate, question: string) {
  const result = yield* candidate.run(question, {name});
  // A stopped or interrupted run fails its branch, so it cannot win the race.
  if (result.status !== "completed")
    throw new TerminalError(`${name} ${result.status}: ${result.reason}`);
  return result.output;
}

export const racingAgents = restate.service({
  name: "RacingAgents",
  handlers: {
    answer: restate.schemas(
      {
        input: z.object({
          question: z
            .string()
            .max(4000)
            .default("How should a durable workflow handle external side effects?"),
        }),
        output: z.string(),
      },
      function* ({question}) {
        const tasks = Object.entries(candidates).map(([name, candidate]) =>
          restate.spawn(answerWith(name, candidate, question)),
        );
        try {
          // any waits for success: a fast failure must not defeat a healthy peer.
          return yield* restate.any(tasks);
        } catch (error) {
          if (error instanceof AggregateError)
            throw new TerminalError("Neither candidate produced a completed answer");
          throw error;
        } finally {
          // Join after interruption so model AbortSignals and tool cleanup run.
          for (const task of tasks) task.interrupt();
          yield* restate.allSettled(tasks);
        }
      },
    ),
  },
});
