/**
 * Interrupt & Regenerate
 *
 * Interruptions are messages sent to the agent while it is already working.
 * For coding agents, this is critical: a task can take a while, and you may
 * see the agent going off in the wrong direction and want to add missing
 * context to get it back on track.
 *
 * Restate lets us express interruptions using cancellation signals. Cancelling
 * an invocation raises a TerminalError at the next Restate await inside the
 * target handler. The error propagates through sub-invocations, giving us
 * stack-unwinding semantics across a distributed call tree, and leaves room
 * for durable cleanup (notifying the orchestrator, releasing resources, etc.).
 */
import * as restate from "@restatedev/restate-sdk";
import {
  CancelledError,
  Context,
  InvocationIdParser,
  ObjectContext,
  ObjectSharedContext,
  TerminalError,
} from "@restatedev/restate-sdk";
import { ModelMessage } from "ai";
import { z } from "zod";
import llmCall from "./utils/llm";

const schema = restate.serde.schema;

const UserMessage = z.object({
  content: z.string().default("Build me a small todo CLI in Python."),
});
type UserMessage = z.infer<typeof UserMessage>;

const AssistantMessage = z.object({
  content: z.string(),
  final: z.boolean().default(false),
});
type AssistantMessage = z.infer<typeof AssistantMessage>;

type TaskInput = {
  agentId: string;
  messages: ModelMessage[];
};

// Forward type references — services reference each other, but types are
// hoisted so `typeof` works regardless of declaration order.
type CodingAgent = typeof codingAgent;
type CodingTask = typeof codingTask;

// <start_here>
// ORCHESTRATOR VIRTUAL OBJECT
const codingAgent = restate.object({
  name: "CodingAgent",
  handlers: {
    /** Receive a user message. A new message interrupts any ongoing task. */
    message: restate.createObjectHandler(
      { input: schema(UserMessage) },
      async (ctx: ObjectContext, msg: UserMessage) => {
        // (1) Access state of the Virtual Object
        const messages = (await ctx.get<ModelMessage[]>("messages")) ?? [];
        messages.push({ role: "user", content: msg.content });

        // (2) Interrupt the ongoing task and wait for its cleanup to finish
        const currentTaskId = await ctx.get<string>("current_task_id");
        if (currentTaskId) {
          await cancelAndWait(ctx, currentTaskId);
        }

        // (3) Start executing the new task
        const handle = ctx
          .serviceSendClient<CodingTask>({ name: "CodingTask" })
          .runTask({ agentId: ctx.key, messages });

        // (4) Store the handle to the task and persist the updated history
        const invocationId = await handle.invocationId;
        ctx.set("current_task_id", invocationId);
        ctx.set("messages", messages);
      },
    ),

    /** Callback used by CodingTask.runTask to stream progress back into history. */
    appendMessage: restate.createObjectHandler(
      { input: schema(AssistantMessage) },
      async (ctx: ObjectContext, msg: AssistantMessage) => {
        const messages = (await ctx.get<ModelMessage[]>("messages")) ?? [];
        messages.push({ role: "assistant", content: msg.content });
        ctx.set("messages", messages);
        if (msg.final) {
          ctx.clear("current_task_id");
        }
      },
    ),

    getHistory: restate.createObjectSharedHandler(
      async (ctx: ObjectSharedContext) =>
        (await ctx.get<ModelMessage[]>("messages")) ?? [],
    ),
  },
});

/**
 * Cancel an invocation and block until it finishes its cleanup, up to `timeoutMs`.
 *
 * Waiting for the cancelled invocation ensures any durable cleanup it runs is
 * observed before the caller moves on (e.g. to undo some completed task).
 */
async function cancelAndWait(
  ctx: Context,
  invocationId: string,
  timeoutMs: number = 30_000,
): Promise<void> {
  const id = InvocationIdParser.fromString(invocationId);
  ctx.cancel(id);
  try {
    await ctx.attach(id).orTimeout(timeoutMs);
  } catch (err) {
    // Expected: the cancelled invocation finishes with a TerminalError.
    if (!(err instanceof TerminalError)) throw err;
  }
}
// <end_here>

// LONG-RUNNING TASK SERVICE
const codingTask = restate.service({
  name: "CodingTask",
  handlers: {
    /**
     * Multi-step coding task. If interrupted, surfaces as TerminalError
     * at the next Restate await — we catch it, run cleanup, and re-raise.
     */
    runTask: async (ctx: Context, inp: TaskInput) => {
      const steps = [
        ["plan", "Outline a high-level design for the user's latest request."],
        ["draft", "Write a first implementation based on the plan."],
        ["polish", "Refine and clean up the draft."],
      ] as const;

      const conversation: ModelMessage[] = [...inp.messages];
      try {
        for (let i = 0; i < steps.length; i++) {
          const [label, prompt] = steps[i];
          const { text } = await ctx.run(
            `LLM: ${label}`,
            () =>
              llmCall([
                ...conversation,
                { role: "user", content: prompt },
              ]),
            { maxRetryAttempts: 3 },
          );
          conversation.push({ role: "assistant", content: text });
          ctx
            .objectSendClient<CodingAgent>(
              { name: "CodingAgent" },
              inp.agentId,
            )
            .appendMessage({
              content: text,
              final: i === steps.length - 1,
            });
        }
      } catch (err) {
        if (err instanceof TerminalError) {
            // Cancellations surface as CancelledError. Only run the
            // cancellation-specific cleanup for those; let other terminal
            // errors propagate with a generic cleanup note.
            const content =
                err instanceof CancelledError
                    ? "[task cleanup ran after cancellation]"
                    : "[task cleanup ran after error]";
            ctx
                .objectSendClient<CodingAgent>(
                    { name: "CodingAgent" },
                    inp.agentId,
                )
                .appendMessage({ content, final: true });
        }
        throw err;
      }
    },
  },
});

restate.serve({ services: [codingAgent, codingTask], port: 9080 });
