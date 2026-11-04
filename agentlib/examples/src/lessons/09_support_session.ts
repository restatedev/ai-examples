// 09: Keep a conversation in a keyed object and control its running turn.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent, asyncTool, LazyStateConversation} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model, logApprovalCommand} from "../shared.js";

type ActiveTurn = {invocationId: string};

const support = agent({
  name: "support",
  model,
  instructions:
    "Help with the user's task. Look up tickets before changing them.",
  tools: {
    lookupTicket: asyncTool({
      description: "Look up a demo support ticket. No ticketing system is called.",
      input: z.object({ticket: z.string()}),
      async execute({ticket}) {
        return {ticket, status: "open"};
      },
    }),
    closeTicket: asyncTool({
      description: "Close a demo ticket. No external ticket is changed.",
      input: z.object({ticket: z.string()}),
      needsApproval: true,
      async execute({ticket}) {
        return {ticket, status: "closed"};
      },
    }),
  },
});

/** One session per key. Turns run one at a time; the shared handlers inspect and control them. */
export const aiSession = restate.object({
  name: "AiSession",
  handlers: {
    doTurn: restate.schemas(
      {
        input: z.object({
          message: z
            .string()
            .default("Look up ticket T-42, then close it."),
        }),
        output: z.string(),
      },
      function* ({message}) {
        // The conversation lives in this object's state; long ones are summarized.
        const conversation = new LazyStateConversation({
          compaction: {model, policy: {maxMessages: 64, retainMessages: 12}},
        });
        restate.state().set("active", {invocationId: restate.handlerRequest().id});
        try {
          const result = yield* support.run(message, {
            conversation,
            steeringSignal: "steering",
            interruptSignal: "interrupt",
            *onApproval(request) {
              logApprovalCommand("AiSession", request);
            },
          });
          if (result.status !== "completed") return result.output ?? result.reason;
          return result.output;
        } finally {
          restate.state().clear("active");
        }
      },
    ),
    *status() {
      return {
        active: yield* restate.sharedState().get<ActiveTurn>("active"),
      };
    },
    *history() {
      return yield* new LazyStateConversation().page();
    },
    steer: restate.schemas(
      {
        input: z.object({message: z.string().default("Only look up the ticket; do not close it.")}),
        output: z.boolean(),
      },
      function* ({message}) {
        return yield* signalActiveTurn("steering", message);
      },
    ),
    interrupt: restate.schemas(
      {
        input: z.object({reason: z.string().default("Stop this task; I no longer need the result.")}),
        output: z.boolean(),
      },
      function* ({reason}) {
        return yield* signalActiveTurn("interrupt", reason);
      },
    ),
    approve: restate.schemas(
      {
        input: z.object({
          invocationId: z.string().describe("Use invocationId from the logged approval command."),
          signalName: z.string().describe("Use signalName from the logged approval command."),
          approved: z.boolean().default(false),
        }),
        output: z.boolean(),
      },
      function* ({invocationId, signalName, approved}) {
        restate.invocation(invocationId).signal(signalName).resolve(approved);
        return true;
      },
    ),
  },
  options: {
    // Shared handlers run while doTurn holds the object's lock.
    handlers: {
      status: {shared: true},
      history: {shared: true},
      steer: {shared: true},
      interrupt: {shared: true},
      approve: {shared: true},
    },
  },
});

/** Deliver a control to the running turn; false when no turn is active. */
function* signalActiveTurn(name: string, value: string): restate.Operation<boolean> {
  const active = yield* restate.sharedState().get<ActiveTurn>("active");
  if (!active) return false;
  restate.invocation(active.invocationId).signal(name).resolve(value);
  return true;
}
