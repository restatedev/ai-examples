// 01: Run an agent inside a Restate handler. Each request starts a fresh conversation.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent} from "@restatedev/agentlib";
import {z} from "zod";
import {openai} from "@ai-sdk/openai";
import {aiModel} from "@restatedev/agentlib/provider";

// aiModel runs a Vercel AI SDK model. To use another provider, pass a model from its
// AI SDK package instead of openai(...).
const model = aiModel({model: openai(process.env.AGENT_MODEL ?? "gpt-5.4")});

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
