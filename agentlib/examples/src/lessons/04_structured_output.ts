// 04: Describe the result with a schema so callers receive validated, typed data.
import {TerminalError} from "@restatedev/restate-sdk";
import * as restate from "@restatedev/restate-sdk-gen";
import {agent} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

const classificationSchema = z.object({
  category: z.enum(["billing", "technical", "other"]),
  summary: z.string(),
});

const triage = agent({
  model,
  instructions: "Classify the support request and summarize it in one sentence.",
  output: classificationSchema,
});

export const ticketTriage = restate.service({
  name: "TicketTriage",
  handlers: {
    classify: restate.schemas(
      {
        input: z.object({
          message: z.string().default("I was charged twice for my subscription. Please help me get a refund."),
        }),
        output: classificationSchema,
      },
      function* ({message}) {
        const result = yield* triage.run(message);
        if (result.status !== "completed")
          throw new TerminalError(`Triage ${result.status}: ${result.reason}`);
        return result.output;
      },
    ),
  },
});
