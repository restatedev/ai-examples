// 12: Use a structured decision to route a request to one specialist.
import {TerminalError} from "@restatedev/restate-sdk";
import * as restate from "@restatedev/restate-sdk-gen";
import {agent} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

const route = agent({
  model,
  maxSteps: 2,
  instructions:
    "Choose the one specialist best suited to answer the customer question. Classify only; do not answer it.",
  output: z.object({specialist: z.enum(["billing", "account", "product"])}),
});

const specialists = {
  billing: agent({
    model,
    instructions:
      "Help with payments, charges, and refunds. Do not claim to have changed an order.",
  }),
  account: agent({
    model,
    instructions: "Help with sign-in and account access. Never ask for a password.",
  }),
  product: agent({
    model,
    instructions: "Explain product features and how to use them. Admit when details are unknown.",
  }),
};

export const supportRouter = restate.service({
  name: "SupportRouter",
  handlers: {
    answer: restate.schemas(
      {
        input: z.object({
          question: z.string().default("I can't log into my account. How can I regain access?"),
        }),
        output: z.string(),
      },
      function* ({question}) {
        const routed = yield* route.run(question);
        if (routed.status !== "completed")
          throw new TerminalError(`Router ${routed.status}: ${routed.reason}`);
        const {specialist} = routed.output;
        const result = yield* specialists[specialist].run(question);
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
  },
});
