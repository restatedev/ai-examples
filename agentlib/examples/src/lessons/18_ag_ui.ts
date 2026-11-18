// 18: Serve an agent to AG-UI clients, such as CopilotKit.
//
// AG-UI (https://docs.ag-ui.com) streams an agent run to a UI as server-sent
// events. Here the agent runs in a Restate object, one per AG-UI thread, and
// appends the AG-UI events of its work to the object's state. The HTTP handler
// at the bottom only reads them. So closing the stream does not stop the turn,
// and a turn that waits for the client, to approve a call or to run one of
// the client's own tools, ends the AG-UI run while the turn waits on a
// durable signal, holding no process, until a later run answers it.
import type {IncomingMessage, ServerResponse} from "node:http";
import {setTimeout as delay} from "node:timers/promises";
import {EventType, type Event, type Interrupt, type Message as AgUiMessage} from "@ag-ui/core";
import {RunAgentInputSchema} from "@ag-ui/core/schemas";
import {TerminalError} from "@restatedev/restate-sdk";
import {connect, rpc} from "@restatedev/restate-sdk-clients";
import * as restate from "@restatedev/restate-sdk-gen";
import {
  agent,
  asyncTool,
  type JsonValue,
  type Message,
  type ProgressEvent,
  type Tool,
} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

const assistant = agent({
  model,
  instructions:
    "AG-UI lesson. Use lookupOrder to answer questions about demo orders. Use cancelOrder to cancel one; a person approves each cancellation.",
  tools: {
    lookupOrder: asyncTool({
      description: "Look up a demo order.",
      input: z.object({orderId: z.string()}),
      async execute({orderId}) {
        return {orderId, status: "shipped"};
      },
    }),
    cancelOrder: asyncTool({
      description: "Cancel a demo order after a person approves. No real order changes.",
      input: z.object({orderId: z.string()}),
      needsApproval: true,
      async execute({orderId}) {
        return {orderId, status: "cancelled"};
      },
    }),
  },
});

/** A tool the client runs itself, such as a CopilotKit frontend tool. */
const clientTool = z.object({
  name: z.string().regex(/^[A-Za-z0-9_-]{1,64}$/),
  description: z.string(),
  parameters: z.record(z.string(), z.unknown()).optional(),
});

/**
 * The thread's log: AG-UI events, plus the markers the HTTP handler turns
 * into runs. A wait ends a run: with the interrupt for an approval, or
 * successfully for a client tool, whose call the client has just received.
 */
type Entry =
  | Event
  | {type: "turn"; messageId: string}
  | {type: "wait"; callId: string; interrupt?: Interrupt}
  | {type: "done"}
  | {type: "failed"; message: string};
/** A call the turn waits for, and where the run that answers it reads on. */
type Pending = {invocationId: string; signalName: string; cursor: number};
/** The turn in progress: where its entries start, and the message it answers. */
type Running = {start: number; messageId: string; message: string};

/** The AG-UI events that show a progress event; the others have no counterpart here. */
function progressEvents(event: ProgressEvent): Event[] {
  if (event.type === "tool-start")
    return [
      {type: EventType.TOOL_CALL_START, toolCallId: event.callId, toolCallName: event.name},
      {
        type: EventType.TOOL_CALL_ARGS,
        toolCallId: event.callId,
        delta: JSON.stringify(event.input),
      },
      {type: EventType.TOOL_CALL_END, toolCallId: event.callId},
    ];
  if (event.type === "tool-end")
    return [
      {
        type: EventType.TOOL_CALL_RESULT,
        messageId: `${event.callId}-result`,
        toolCallId: event.callId,
        // JSON, because clients such as CopilotKit parse a tool result as JSON.
        content: JSON.stringify(event.result),
      },
    ];
  return [];
}

export const agUiThread = restate.object({
  name: "AgUiThread",
  handlers: {
    turn: restate.schemas(
      {
        input: z.object({
          messageId: z.string().default("m1"),
          message: z.string().default("Cancel order O-7."),
          tools: z.array(clientTool).default([]),
        }),
        output: z.void(),
      },
      function* ({messageId, message, tools}) {
        const state = restate.state();
        const invocationId = restate.handlerRequest().id;
        let count = (yield* state.get<number>("count")) ?? 0;
        const append = (...entries: Entry[]) => {
          for (const entry of entries) state.set(`entry-${count++}`, entry);
          state.set("count", count);
        };
        // Turns queue on the object, so each marks where its own events start.
        state.set(`start-${messageId}`, count);
        state.set("running", {start: count, messageId, message} satisfies Running);
        append({type: "turn", messageId});
        const pending: Record<string, Pending> = {};
        const wait = (callId: string, signalName: string, interrupt?: Interrupt) => {
          // A later run reads on right after the wait, so it also gets what
          // the turn appended while no stream was open.
          pending[callId] = {invocationId, signalName, cursor: count + 1};
          state.set("pending", pending);
          append({type: "wait", callId, ...(interrupt ? {interrupt} : {})});
        };
        // The client already holds the results of the tools it ran.
        const ranByClient = new Set<string>();
        const clientTools = Object.fromEntries(
          tools.map(({name, description, parameters}): [string, Tool] => [
            name,
            {
              description,
              inputSchema: parameters ?? {type: "object", properties: {}},
              *execute(_input, {callId}) {
                ranByClient.add(callId);
                const signalName = `client-tool:${callId}`;
                wait(callId, signalName);
                return yield* restate.signal<JsonValue>(signalName);
              },
            },
          ]),
        );
        try {
          const result = yield* assistant.run(message, {
            messages: (yield* state.get<Message[]>("messages")) ?? [],
            tools: clientTools,
            *onProgress(event) {
              if (event.type !== "tool-end" || !ranByClient.has(event.callId))
                append(...progressEvents(event));
              if (event.type === "tool-end" && event.callId in pending) {
                delete pending[event.callId];
                state.set("pending", pending);
              }
            },
            *onApproval({signalName, call}) {
              wait(call.id, signalName, {
                id: call.id,
                reason: "tool_approval",
                toolCallId: call.id,
                message: `Allow ${call.name} with ${JSON.stringify(call.input)}?`,
                responseSchema: {
                  type: "object",
                  properties: {approved: {type: "boolean"}},
                  required: ["approved"],
                },
              });
            },
          });
          state.set("messages", result.messages);
          const text = result.status === "completed" ? result.output : (result.output ?? "");
          const answerId = `${invocationId}-answer`;
          append(
            {type: EventType.TEXT_MESSAGE_START, messageId: answerId, role: "assistant"},
            // A content event must carry a non-empty delta.
            ...(text
              ? [{type: EventType.TEXT_MESSAGE_CONTENT, messageId: answerId, delta: text} as const]
              : []),
            {type: EventType.TEXT_MESSAGE_END, messageId: answerId},
            {type: "done"},
          );
        } catch (error) {
          if (!(error instanceof TerminalError)) throw error;
          append({type: "failed", message: error.message});
        } finally {
          state.clear("pending");
          state.clear("running");
        }
      },
    ),
    /** Where the turn for a message starts, or where the next turn will. */
    *locate(messageId: string) {
      const state = restate.sharedState();
      return (
        (yield* state.get<number>(`start-${messageId}`)) ?? (yield* state.get<number>("count")) ?? 0
      );
    },
    /** The finished conversation and the turn in progress, for a client that reconnects. */
    *connect() {
      const state = restate.sharedState();
      return {
        messages: (yield* state.get<Message[]>("messages")) ?? [],
        running: (yield* state.get<Running>("running")) ?? undefined,
      };
    },
    /** Up to 100 entries, starting at `after`; null for a wait already answered. */
    *read(after: number) {
      const state = restate.sharedState();
      const pending = (yield* state.get<Record<string, Pending>>("pending")) ?? {};
      const end = Math.min((yield* state.get<number>("count")) ?? 0, after + 100);
      const entries: (Entry | null)[] = [];
      for (let i = after; i < end; i++) {
        const entry = (yield* state.get<Entry>(`entry-${i}`))!;
        entries.push(entry.type === "wait" && !(entry.callId in pending) ? null : entry);
      }
      return entries;
    },
    /** The calls waiting for the client. */
    *waiting() {
      return Object.keys(
        (yield* restate.sharedState().get<Record<string, Pending>>("pending")) ?? {},
      );
    },
    /** Answers a waiting call and returns where the run that answered it reads on. */
    *answer({callId, value}: {callId: string; value: JsonValue}) {
      const pending = yield* restate.sharedState().get<Record<string, Pending>>("pending");
      const waiting = pending?.[callId];
      if (!waiting) throw new TerminalError(`Interrupt ${callId} is not waiting for an answer`);
      restate.invocation(waiting.invocationId).signal(waiting.signalName).resolve(value);
      return waiting.cursor;
    },
  },
  // Shared handlers read and answer while a turn runs.
  options: {
    handlers: {
      locate: {shared: true},
      connect: {shared: true},
      read: {shared: true},
      waiting: {shared: true},
      answer: {shared: true},
    },
  },
});

/** A finished conversation as AG-UI messages, with the turn in progress. */
function snapshot(threadId: string, messages: Message[], running?: Running): AgUiMessage[] {
  const shown = messages.map((message, index): AgUiMessage => {
    const id = `${threadId}-${index}`;
    if (message.role === "user") return {id, role: "user", content: message.content};
    if (message.role === "tool")
      return {
        id,
        role: "tool",
        toolCallId: message.callId,
        content: JSON.stringify(message.result),
      };
    const toolCalls = message.calls?.map((call) => ({
      id: call.id,
      type: "function" as const,
      function: {name: call.name, arguments: JSON.stringify(call.input)},
    }));
    return {id, role: "assistant", content: message.content, ...(toolCalls ? {toolCalls} : {})};
  });
  if (running) shown.push({id: running.messageId, role: "user", content: running.message});
  return shown;
}

/** The client's answer to a tool it ran: JSON when its text parses, the text otherwise. */
function toolOutput(parts: string | {type: string; text?: string}[]): JsonValue {
  const content = typeof parts === "string" ? parts : parts.map((part) => part.text ?? "").join("");
  try {
    return JSON.parse(content) as JsonValue;
  } catch {
    return content;
  }
}

/**
 * AG-UI's HTTP transport as a Node request handler: POST a RunAgentInput, read
 * the run as server-sent events. A run does the first of these that applies:
 * - with `resume`, it answers the approval that ended the previous run;
 * - with tool messages last, it answers the client tools the turn waits for;
 * - with a user message last, it sends that message as a turn, once per
 *   message ID, so a retried or reconnecting run follows the same turn;
 * - otherwise it reconnects: the conversation as a snapshot, then the turn
 *   in progress, if any.
 * Each run follows its turn until the turn answers or waits for the client.
 */
export function agUiHandler(ingressUrl: string) {
  const ingress = connect({url: ingressUrl});
  async function handle(request: IncomingMessage, response: ServerResponse) {
    const parsed = RunAgentInputSchema.safeParse(await readJson(request));
    if (!parsed.success) {
      response.writeHead(400).end("Expected an AG-UI RunAgentInput");
      return;
    }
    const {threadId, runId, messages, resume, tools} = parsed.data;
    const thread = ingress.client(agUiThread, threadId);
    let closed = false;
    response.on("close", () => (closed = true));
    response.writeHead(200, {"Content-Type": "text/event-stream", "Cache-Control": "no-store"});
    const send = (event: Event) => response.write(`data: ${JSON.stringify(event)}\n\n`);
    const finish = (interrupt?: Interrupt) =>
      send({
        type: EventType.RUN_FINISHED,
        threadId,
        runId,
        outcome: interrupt ? {type: "interrupt", interrupts: [interrupt]} : {type: "success"},
      });
    send({type: EventType.RUN_STARTED, threadId, runId});
    try {
      // The turn whose entries this run shows; undefined follows from the cursor on.
      let turn: string | undefined;
      let cursor: number;
      const waiting = new Set(await thread.waiting());
      const lastOther = messages.findLastIndex((message) => message.role !== "tool");
      const results = messages
        .slice(lastOther + 1)
        .filter((message) => message.role === "tool" && waiting.has(message.toolCallId));
      const last = messages.at(-1);
      if (resume?.[0]) {
        const {interruptId, status, payload} = resume[0];
        const approved = status === "resolved" && payload?.approved === true;
        cursor = await thread.answer({callId: interruptId, value: approved});
      } else if (results.length) {
        const cursors = [];
        for (const result of results)
          if (result.role === "tool")
            cursors.push(
              await thread.answer({callId: result.toolCallId, value: toolOutput(result.content)}),
            );
        cursor = Math.min(...cursors);
      } else if (last?.role === "user") {
        if (typeof last.content !== "string") throw new Error("A user message must be text");
        const message = {messageId: last.id, message: last.content, tools};
        await ingress
          .sendClient(agUiThread, threadId)
          .turn(message, rpc.sendOpts({idempotencyKey: last.id}));
        turn = last.id;
        cursor = await thread.locate(last.id);
      } else {
        const {messages: finished, running} = await thread.connect();
        send({
          type: EventType.MESSAGES_SNAPSHOT,
          messages: snapshot(threadId, finished, running),
        });
        if (!running) return finish();
        turn = running.messageId;
        cursor = running.start;
      }
      // The state is the source of truth, so polling it is enough for a lesson.
      let following = turn === undefined;
      while (!closed) {
        const entries = await thread.read(cursor);
        if (!entries.length) await delay(200);
        cursor += entries.length;
        for (const entry of entries) {
          if (!entry) continue;
          if (entry.type === "turn") following ||= entry.messageId === turn;
          else if (!following) continue;
          else if (entry.type === "wait") return finish(entry.interrupt);
          else if (entry.type === "done") return finish();
          else if (entry.type === "failed")
            return send({type: EventType.RUN_ERROR, message: entry.message});
          else send(entry);
        }
      }
    } catch (error) {
      send({
        type: EventType.RUN_ERROR,
        message: error instanceof Error ? error.message : String(error),
      });
    } finally {
      response.end();
    }
  }
  return (request: IncomingMessage, response: ServerResponse) => {
    handle(request, response).catch(() => response.destroy());
  };
}

async function readJson(request: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) chunks.push(chunk as Buffer);
  try {
    return JSON.parse(Buffer.concat(chunks).toString());
  } catch {
    return undefined;
  }
}
