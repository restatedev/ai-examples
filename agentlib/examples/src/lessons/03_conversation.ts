// 03: Keep conversation history between requests to the same object key.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent, type Message} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

const assistant = agent({
  model,
  instructions: "Use the conversation to remember what the user told you.",
});

export const chatSession = restate.object({
  name: "ChatSession",
  handlers: {
    ask: restate.schemas(
      {
        input: z.object({
          message: z.string().default("My name is Bob. Remember it for our next conversation."),
        }),
        output: z.string(),
      },
      function* ({message}) {
        const messages = (yield* restate.state().get<Message[]>("messages")) ?? [];
        const result = yield* assistant.run(message, {messages});
        restate.state().set("messages", result.messages);
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
  },
});
