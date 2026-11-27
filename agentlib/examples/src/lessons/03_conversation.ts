// 03: Keep conversation history between requests to the same object key.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent, Conversation} from "@restatedev/agentlib";
import {z} from "zod";
import {openai} from "@ai-sdk/openai";
import {aiModel} from "@restatedev/agentlib/provider";

const model = aiModel({model: openai(process.env.AGENT_MODEL ?? "gpt-5.4")});

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
        // The run loads the conversation from this object's state and saves its progress there.
        const result = yield* assistant.run(message, {conversation: new Conversation()});
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
    /** Up to 100 saved messages from index `from`, including the ones a summary replaced. */
    *history(from: number) {
      return yield* new Conversation().page(from);
    },
  },
  options: {
    // Restate sends these keys with each request. The run reads the message chunks on demand.
    state: {preload: ["conversation/meta", "conversation/summary"]},
    // history reads the conversation while ask runs.
    handlers: {history: {shared: true}},
  },
});
