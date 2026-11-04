// 01: Run an agent inside a Restate handler. Each request starts a fresh conversation.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

const assistant = agent({model});

export const hello = restate.service({
  name: "Hello",
  handlers: {
    ask: restate.schemas(
      {input: z.object({message: z.string().default("Say hello in one sentence.")}), output: z.string()},
      function* ({message}) {
        const result = yield* assistant.run(message);
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
  },
});
