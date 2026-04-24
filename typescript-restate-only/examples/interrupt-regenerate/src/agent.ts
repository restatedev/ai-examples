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

const ChatMessage = z.object({
  content: z.string().default("Build me a small todo CLI in Python."),
});
type ChatMessage = z.infer<typeof ChatMessage>;

type TaskInput = {
  agentId: string;
  messages: ModelMessage[];
};

// Forward type references — services reference each other, but types are
// hoisted so `typeof` works regardless of declaration order.
type CodingAgent = typeof codingAgent;
type CodingTask = typeof codingTask;

const TASK_PROMPT =
  "Take the user's latest request and respond with a full answer: " +
  "first outline a high-level plan, then write a draft implementation, " +
  "then polish it into a final version.";

// ORCHESTRATOR VIRTUAL OBJECT
const codingAgent = restate.object({
  name: "CodingAgent",
  handlers: {
    // <start_message_handler>
    /** Receive a user message. A new message interrupts any ongoing task. */
    message: restate.createObjectHandler(
      { input: schema(ChatMessage) },
      async (ctx: ObjectContext, msg: ChatMessage) => {
        // (1) Access state of the Virtual Object
        const messages = (await ctx.get<ModelMessage[]>("messages")) ?? [];
        messages.push({ role: "user", content: msg.content });

        // (2) Interrupt the ongoing task and wait for its cleanup to finish.
        // The cancelled invocation finishes with a TerminalError; swallow it.
        const currentTaskId = await ctx.get<string>("current_task_id");
        if (currentTaskId) {
          const id = InvocationIdParser.fromString(currentTaskId);
          ctx.cancel(id);
          try {
            await ctx.attach(id).orTimeout(30_000);
          } catch (err) {
            if (!(err instanceof TerminalError)) throw err;
          }
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
    // <end_message_handler>

    /** Callback used by CodingTask.runTask to stream progress back into history. */
    appendMessage: restate.createObjectHandler(
      { input: schema(ChatMessage) },
      async (ctx: ObjectContext, msg: ChatMessage) => {
        const messages = (await ctx.get<ModelMessage[]>("messages")) ?? [];
        messages.push({ role: "assistant", content: msg.content });
        ctx.set("messages", messages);
        ctx.clear("current_task_id");
      },
    ),

    getHistory: restate.createObjectSharedHandler(
      async (ctx: ObjectSharedContext) =>
        (await ctx.get<ModelMessage[]>("messages")) ?? [],
    ),
  },
});

// LONG-RUNNING TASK SERVICE
const codingTask = restate.service({
  name: "CodingTask",
  handlers: {
    // <start_run_task>
    /**
     * Long-running coding task. If interrupted, the cancellation surfaces
     * as TerminalError at the next Restate await — we catch it, run durable
     * cleanup, and re-raise so Restate records the invocation as cancelled.
     */
    runTask: async (ctx: Context, inp: TaskInput) => {
      try {
        const { text } = await ctx.run(
          "LLM call",
          () =>
            llmCall([
              ...inp.messages,
              { role: "user", content: TASK_PROMPT },
            ]),
          { maxRetryAttempts: 3 },
        );
        ctx
          .objectSendClient<CodingAgent>({ name: "CodingAgent" }, inp.agentId)
          .appendMessage({ content: text });
      } catch (err) {
        if (err instanceof TerminalError) {
          const content =
            err instanceof CancelledError
              ? "[task cleanup ran after cancellation]"
              : "[task cleanup ran after error]";
          ctx
            .objectSendClient<CodingAgent>({ name: "CodingAgent" }, inp.agentId)
            .appendMessage({ content });
        }
        throw err;
      }
    },
    // <end_run_task>
  },
});

restate.serve({ services: [codingAgent, codingTask], port: 9080 });
