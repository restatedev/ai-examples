import assert from "node:assert/strict";
import {execFile} from "node:child_process";
import {promisify} from "node:util";
import {after, before, mock, test} from "node:test";
import {setTimeout as delay} from "node:timers/promises";
import {TerminalError} from "@restatedev/restate-sdk";
import {connect} from "@restatedev/restate-sdk-clients";
import {RestateContainer, RestateTestEnvironment} from "@restatedev/restate-sdk-testcontainers";
import * as r from "@restatedev/restate-sdk-gen";
import {
  journaledModel,
  type Model,
  type ModelRequest,
  type ModelResponse,
  type ToolResult,
} from "@restatedev/agentlib";

const sources = [
  {
    id: "durability",
    title: "Recovery",
    text: "Completed journal entries are replayed without repeating the action.",
  },
  {
    id: "idempotency",
    title: "External effects",
    text: "Use stable idempotency keys for external mutations.",
  },
];
const effects = new Map<string, number>();
const peerEffects = new Map<string, number>();
const cleanedRaces = new Set<string>();
const answer = (output: unknown): ModelResponse => ({type: "final", text: JSON.stringify(output)});
type PeerReviewRequest = {brief: string; draft: string; focus: "requirements" | "clarity"};

// Both workers must reach this barrier before either can finish: serialization
// would deadlock and fail the test's timeout.
const barrier = r.object({
  name: "ResearchBarrier",
  handlers: {
    *arrive(id: string) {
      const participants = (yield* r.state().get<string[]>("participants")) ?? [];
      participants.push(id);
      r.state().set("participants", participants);
      if (participants.length === 2) {
        for (const participant of participants)
          r.invocation(participant).signal("workers-ready").resolve(true);
        // Ready for the next report's workers.
        r.state().clear("participants");
      }
    },
  },
});

const researchModel: Model = function* (request) {
  const role = request.instructions!.split(".")[0];
  const invocationId = r.handlerRequest().id;
  if (role === "Research worker" && prompt(request) === "cite without reading") {
    // The first answer cites a source it never read; afterRun's reason comes back
    // as a note, and the worker reads the source before answering again.
    if (!/did not read/.test(JSON.stringify(request.messages)))
      return answer({answer: "Unsupported claim", sourceIds: ["durability"]});
    if (!request.messages.some((message) => message.role === "tool"))
      return {
        type: "tool_calls",
        calls: [{id: "read-durability", name: "readSource", input: {id: "durability"}}],
      };
    return answer({answer: "Supported claim", sourceIds: ["durability"]});
  }
  if (role === "Research worker" && request.step === 1) {
    yield* r.client(barrier, "parallel").arrive(invocationId);
    yield* r.signal("workers-ready");
  }
  return yield* r.run(
    async (): Promise<ModelResponse> => {
      const key = `${invocationId}:${role}:${request.step}`;
      effects.set(key, (effects.get(key) ?? 0) + 1);
      if (role === "Research planner")
        return answer({
          questions: ["How does recovery work?", "How do external effects avoid duplication?"],
        });
      if (role === "Research worker") {
        if (request.step === 1)
          return {
            type: "tool_calls",
            calls: sources.map((source) => ({
              id: source.id,
              name: "readSource",
              input: {id: source.id},
            })),
          };
        assert.equal(request.messages.filter((message) => message.role === "tool").length, 2);
        return answer({
          answer: "Replay preserves completed results; external mutations need idempotency.",
          sourceIds: sources.map((source) => source.id),
        });
      }
      assert.match(JSON.stringify(request.messages), /external mutations need idempotency/);
      return {
        type: "final",
        text: "Recovery uses replay [durability]; external effects use idempotency keys [idempotency].",
      };
    },
    {name: `fixture:${role}`},
  );
};

const reviewCounts = new Map<string, number>();
const reviewModel: Model = function* (request) {
  const input = lastPrompt(request);
  return yield* r.run(
    async () => {
      if (request.instructions?.startsWith("Code writer")) {
        if (input.startsWith("Revise")) {
          // A revision request carries only the feedback; the draft comes from the
          // writer's conversation.
          assert.match(input, /empty input/);
          assert.match(JSON.stringify(request.messages), /items\[0\]\.value/);
          return answer({code: "return items.length ? items[0] : undefined;"});
        }
        return answer({code: "return items[0].value;"});
      }
      const {task, code} = JSON.parse(input) as {task: string; code: string};
      reviewCounts.set(task, (reviewCounts.get(task) ?? 0) + 1);
      return answer({
        approved: task !== "always reject" && code.includes("items.length"),
        feedback: "Handle empty input.",
      });
    },
    {name: "fixture:code"},
  );
};

function prompt(request: Parameters<Model>[0]) {
  const message = request.messages.find((message) => message.role === "user");
  assert.ok(message && message.role === "user");
  return message.content;
}
/** The newest user message. Earlier ones can come from previous runs on the same key. */
function lastPrompt(request: Parameters<Model>[0]) {
  const message = request.messages.findLast((message) => message.role === "user");
  assert.ok(message && message.role === "user");
  return message.content;
}
const racingModels = {
  *quick(request) {
    const input = prompt(request);
    if (input === "fallback" || input === "both fail")
      throw new TerminalError("Quick model failed");
    if (input === "stopped quick")
      return {
        type: "tool_calls",
        calls: [{id: `unknown-${request.step}`, name: "unknown", input: {}}],
      };
    yield* r.sleep(20);
    return {type: "final", text: "Quick answer"};
  },
  *thorough(request) {
    const input = prompt(request);
    if (input === "both fail") throw new TerminalError("Thorough model failed");
    if (input === "fallback" || input === "stopped quick") {
      yield* r.sleep(10);
      return {type: "final", text: "Thorough answer"};
    }
    const invocationId = r.handlerRequest().id;
    try {
      yield* r.sleep(60000);
      return {type: "final", text: "Should have been cancelled"};
    } finally {
      yield* r.run(
        async () => {
          cleanedRaces.add(invocationId);
          return null;
        },
        {name: "record-race-cleanup"},
      );
    }
  },
} satisfies Record<string, Model>;

const tutorialModel = journaledModel(async (request): Promise<ModelResponse> => {
  if (request.tools.length > 0) {
    if (request.step === 1)
      return {
        type: "tool_calls",
        calls: [{id: "ticket", name: "lookupTicket", input: {ticketId: "T-42"}}],
      };
    const result = request.messages.at(-1);
    assert.equal(result?.role, "tool");
    assert.deepEqual(result.result, {
      status: "success",
      output: {ticketId: "T-42", status: "open"},
    });
    return {type: "final", text: "Ticket T-42 is open."};
  }
  if (request.outputSchema)
    return answer({category: "billing", summary: "Duplicate subscription charge."});
  const turns = request.messages.filter((message) => message.role === "user");
  return {type: "final", text: turns.map((message) => message.content).join(" | ")};
});

/** Example 19's writer: loads the release-notes skill, reads its template, and
 * answers with the template's first line. */
function skillsModel(request: ModelRequest): ModelResponse {
  assert.match(request.instructions!, /- release-notes: Write release notes/);
  assert.match(request.instructions!, /- incident-summary: Summarize a production incident/);
  if (request.step === 1)
    return {
      type: "tool_calls",
      calls: [{id: "load", name: "load_skill", input: {name: "release-notes"}}],
    };
  if (request.step === 2)
    return {
      type: "tool_calls",
      calls: [
        {
          id: "read",
          name: "read_skill_file",
          input: {name: "release-notes", path: "template.md"},
        },
      ],
    };
  const [skill, template] = request.messages.flatMap((message) =>
    message.role === "tool" &&
    message.result.status === "success" &&
    typeof message.result.output === "string"
      ? [message.result.output]
      : [],
  );
  assert.match(skill!, /^# Release notes/);
  return {type: "final", text: template!.split("\n")[0]!};
}

/** Example 20's investigator and its forks, which share its instructions. Each
 * fork checks that it starts from the logs the investigator read. */
function investigation(request: ModelRequest): ModelResponse {
  const results = new Map<string, ToolResult>();
  for (const message of request.messages)
    if (message.role === "tool") results.set(message.callId, message.result);
  const copy = request.messages.find(
    (message) => message.role === "user" && message.content.startsWith("[Forked sub-agent]"),
  );
  if (copy?.role === "user") {
    // The investigator's request: the logs it read, but not the calls that started the forks.
    assert.deepEqual(results.get("logs-payments"), {
      status: "success",
      output:
        "11:58 deployed payments v2.3.0\n12:00 database connection pool exhausted (10 of 10 in use)",
    });
    assert.equal(results.has("pool"), false);
    if (copy.content.includes("connection pool")) {
      if (!results.has("deeper"))
        return {
          type: "tool_calls",
          calls: [{id: "deeper", name: "investigate", input: {task: "Check the database"}}],
        };
      const nested = results.get("deeper");
      assert.equal(nested?.status === "error" && nested.code, "fork_nested");
      return {type: "final", text: "Supported: the pool ran out two minutes after the deploy."};
    }
    // A fork calls tools of its own; the investigator never sees these calls.
    if (!results.has("logs-inventory"))
      return {
        type: "tool_calls",
        calls: [{id: "logs-inventory", name: "readLogs", input: {service: "inventory"}}],
      };
    return {type: "final", text: "Rejected: inventory answers within 80ms."};
  }
  if (!results.has("logs-payments"))
    return {
      type: "tool_calls",
      calls: [
        {id: "logs-checkout", name: "readLogs", input: {service: "checkout"}},
        {id: "logs-payments", name: "readLogs", input: {service: "payments"}},
      ],
    };
  if (!results.has("pool"))
    return {
      type: "tool_calls",
      calls: [
        {
          id: "pool",
          name: "investigate",
          input: {task: "The deploy exhausted the connection pool"},
        },
        {id: "stock", name: "investigate", input: {task: "Inventory is slow"}},
      ],
    };
  assert.equal(results.has("logs-inventory"), false);
  const reply = (id: string) => {
    const result = results.get(id);
    assert.ok(result?.status === "success" && typeof result.output === "string");
    return result.output;
  };
  return {type: "final", text: `Payments v2.3.0. ${reply("pool")} ${reply("stock")}`};
}

const fixtureModel: Model = function* (request) {
  const instructions = request.instructions ?? "";
  if (instructions.startsWith("Investigate production incidents.")) return investigation(request);
  if (instructions.startsWith("You write for a software team")) return skillsModel(request);
  if (
    instructions.startsWith("Ticket approval lesson.") ||
    (instructions.startsWith("Help with the user's task.") &&
      request.messages.some((message) => message.role === "user" && message.content === "approve ticket"))
  ) {
    const session = instructions.startsWith("Help with the user's task.");
    // Earlier turns on the same key are in the conversation; look only at this one.
    const turns = request.messages.filter((message) => message.role === "user").length;
    const start = request.messages.findLastIndex((message) => message.role === "user");
    const result = request.messages.slice(start).find((message) => message.role === "tool");
    if (!result) {
      return {
        type: "tool_calls",
        // A conversation rejects a tool-call ID that an earlier turn used.
        calls: [{
          id: `close-ticket-${turns}`,
          name: "closeTicket",
          input: {[session ? "ticket" : "ticketId"]: "T-42"},
        }],
      };
    }
    assert.equal(result.role, "tool");
    if (result.result.status === "denied")
      return {type: "final", text: "Approval denied; ticket T-42 was left unchanged."};
    assert.deepEqual(result.result, {
      status: "success",
      output: session ? {ticket: "T-42", status: "closed"} : {ticketId: "T-42", status: "closed"},
    });
    return {type: "final", text: "Ticket T-42 is closed."};
  }
  if (instructions.startsWith("Help with the user's task.")) {
    const turns = request.messages.filter((message) => message.role === "user");
    if (turns.at(-1)!.content === "interrupt") {
      r.invocation(r.handlerRequest().id).signal("interrupt").resolve("User cancelled");
      // Only the signal can end this wait; a short sleep would race it.
      yield* r.sleep(60000);
    }
    return {type: "final", text: `Session answer; previous turns: ${turns.length - 1}`};
  }
  if (instructions.startsWith("Audit stock.")) {
    const result = request.messages.find((message) => message.role === "tool");
    if (!result)
      return {
        type: "tool_calls",
        calls: [{id: "count", name: "countStock", input: {warehouses: ["Berlin", "Oslo"]}}],
      };
    assert.equal(result.role, "tool");
    assert.deepEqual(result.result, {status: "success", output: {Berlin: 42, Oslo: 28}});
    return {type: "final", text: "Oslo has the least stock."};
  }
  if (instructions.startsWith("Choose the one specialist")) {
    const specialist = prompt(request).includes("feature") ? "product" : "account";
    return answer({specialist});
  }
  if (instructions.startsWith("Help with sign-in")) {
    assert.equal(request.messages.filter((message) => message.role === "user").length, 1);
    return {type: "final", text: "Use the account recovery flow."};
  }
  if (instructions.startsWith("Explain product features"))
    return {type: "final", text: "Here is how the feature works."};
  if (instructions.startsWith("Call bookHotel")) {
    const result = request.messages.find((message) => message.role === "tool");
    if (!result)
      return {
        type: "tool_calls",
        calls: [{id: "booking", name: "bookHotel", input: {hotelId: "H-42"}}],
      };
    assert.equal(result.role, "tool");
    if (result.result.status === "denied")
      return {type: "final", text: "No reservation was made: the quote exceeds the budget."};
    assert.equal(result.result.status, "success");
    return {type: "final", text: "Demo hotel H-42 was reserved."};
  }
  if (instructions.startsWith("Write a concise answer using only facts")) {
    const input = lastPrompt(request);
    const revision = input.startsWith("Revise");
    if (revision) {
      assert.match(input, /requirements: Mention retries and replay\.\nclarity: Use two short sentences\./);
      // The first draft reaches the revision through the author's conversation.
      assert.match(JSON.stringify(request.messages), /First draft\./);
    }
    const stage = revision ? "revision" : "first-draft";
    const invocationId = r.handlerRequest().id;
    return yield* r.run(
      async (): Promise<ModelResponse> => {
        const key = `${invocationId}:${stage}`;
        peerEffects.set(key, (peerEffects.get(key) ?? 0) + 1);
        return {type: "final", text: revision ? "Revised answer." : "First draft."};
      },
      {name: `fixture:${stage}`},
    );
  }
  if (instructions.startsWith("Review the draft for the requested focus")) {
    const input = JSON.parse(prompt(request)) as PeerReviewRequest;
    assert.equal(input.draft, "First draft.");
    const invocationId = r.handlerRequest().id;
    // Both reviewer RPCs must arrive before either can finish.
    yield* r.client(barrier, "peer-review").arrive(invocationId);
    yield* r.signal("workers-ready");
    return yield* r.run(
      async (): Promise<ModelResponse> => {
        const key = `${invocationId}:${input.focus}`;
        peerEffects.set(key, (peerEffects.get(key) ?? 0) + 1);
        const feedback =
          input.focus === "requirements"
            ? "Mention retries and replay."
            : "Use two short sentences.";
        return {type: "final", text: feedback};
      },
      {name: `fixture:${input.focus}`},
    );
  }
  const last = request.messages.at(-1);
  if (last?.role === "user" && last.content.startsWith("The run stopped:"))
    return {type: "final", text: "Stopped as requested."};
  if (instructions.startsWith("Research ")) return yield* researchModel(request);
  if (instructions.startsWith("Code ")) return yield* reviewModel(request);
  if (instructions.startsWith("Quick answer.")) return yield* racingModels.quick(request);
  if (instructions.startsWith("Thorough answer.")) return yield* racingModels.thorough(request);
  if (
    instructions === "" ||
    instructions.startsWith("Use lookupTicket") ||
    instructions.startsWith("Use the conversation") ||
    instructions.startsWith("Classify the support request")
  )
    return yield* tutorialModel(request);
  throw new Error(`Unexpected example instructions: ${instructions}`);
};

// Replace only the external model. Import the same service instances the app serves.
mock.module("@restatedev/agentlib/provider", {
  namedExports: {aiModel: () => fixtureModel},
});
const [
  {hello},
  {ticketLookup},
  {chatSession},
  {ticketTriage},
  {researchReport, researchWorker},
  {codeReview},
  {racingAgents},
  {aiSession},
  {ticketApproval},
  {supportRouter},
  {guardedBooking},
  {peerAuthor, peerReviewer, peerReview},
  {progressFeed, inventoryAudit},
  {skilledWriter},
  {incidentInvestigation},
] = await Promise.all([
  import("../src/lessons/01_hello.ts"),
  import("../src/lessons/02_tools.ts"),
  import("../src/lessons/03_conversation.ts"),
  import("../src/lessons/04_structured_output.ts"),
  import("../src/lessons/08_research_report.ts"),
  import("../src/lessons/05_evaluator_optimizer.ts"),
  import("../src/lessons/07_racing_agents.ts"),
  import("../src/lessons/09_support_session.ts"),
  import("../src/lessons/06_human_approval.ts"),
  import("../src/lessons/12_routing.ts"),
  import("../src/lessons/13_tool_guardrail.ts"),
  import("../src/lessons/15_peer_review_rpc.ts"),
  import("../src/lessons/16_progress_feed.ts"),
  import("../src/lessons/19_skills.ts"),
  import("../src/lessons/20_forked_agents.ts"),
]);

const approvalCommands: string[] = [];
let env: RestateTestEnvironment;
before(
  async () => {
    env = await RestateTestEnvironment.start({
      logger(_metadata, message) {
        const command = String(message).split("\n").find((line) => line.startsWith('curl "localhost:8080/'));
        if (command) approvalCommands.push(command);
      },
      services: [
        hello,
        ticketLookup,
        chatSession,
        ticketTriage,
        barrier,
        researchReport,
        researchWorker,
        codeReview,
        racingAgents,
        aiSession,
        ticketApproval,
        supportRouter,
        guardedBooking,
        peerAuthor,
        peerReviewer,
        peerReview,
        progressFeed,
        inventoryAudit,
        skilledWriter,
        incidentInvestigation,
      ],
      container: () => new RestateContainer().alwaysReplay().disableRetries(),
    });
  },
  {timeout: 60000},
);
after(async () => {
  await env?.stop();
});

const ingress = () => connect({url: env.baseUrl()});

void test("01: each request starts a fresh run", async () => {
  assert.equal(await ingress().client(hello).ask({message: "Hello"}), "Hello");
  assert.equal(await ingress().client(hello).ask({message: "Another request"}), "Another request");
});

void test("02: the model receives the executed tool's result", async () => {
  const result = await ingress().client(ticketLookup).ask({message: "Look up ticket T-42"});
  assert.equal(result, "Ticket T-42 is open.");
});

void test("03: history persists between requests and is isolated by key", async () => {
  const bob = ingress().client(chatSession, "bob");
  assert.equal(await bob.ask({message: "My name is Bob."}), "My name is Bob.");
  assert.equal(await bob.ask({message: "What is my name?"}), "My name is Bob. | What is my name?");
  const alice = ingress().client(chatSession, "alice");
  assert.equal(await alice.ask({message: "What is my name?"}), "What is my name?");
  const {messages, next} = await bob.history(0);
  assert.deepEqual(
    messages.map((message) => message.role),
    ["user", "assistant", "user", "assistant"],
  );
  assert.equal(next, 4);
  assert.deepEqual((await bob.history(2)).messages, messages.slice(2));
});

void test("04: structured output reaches the caller as an object", async () => {
  const result = await ingress().client(ticketTriage).classify({message: "I was charged twice."});
  assert.deepEqual(result, {category: "billing", summary: "Duplicate subscription charge."});
});

void test("routing chooses a specialist with its own conversation", async () => {
  assert.equal(
    await ingress().client(supportRouter, "login").answer({question: "I cannot log into my account."}),
    "Use the account recovery flow.",
  );
  assert.equal(
    await ingress().client(supportRouter, "feature").answer({question: "How does this feature work?"}),
    "Here is how the feature works.",
  );
  // The router and the specialist save their conversations under their own state keys.
  const state = env.stateOf(supportRouter, "login");
  assert.deepEqual(await state.get("router/meta"), {count: 2});
  assert.deepEqual(await state.get("account/meta"), {count: 2});
  assert.equal(await state.get("product/meta"), null);
});

void test("tool policy denies an over-budget booking and permits one within budget", async () => {
  const client = connect({url: env.baseUrl()}).client(guardedBooking);
  assert.match(
    await client.ask({hotelId: "H-42", quotedTotalCents: 12500, maxTotalCents: 10000}),
    /No reservation was made/,
  );
  assert.equal(
    await client.ask({hotelId: "H-42", quotedTotalCents: 12500, maxTotalCents: 15000}),
    "Demo hotel H-42 was reserved.",
  );
});

void test(
  "agents exchange parallel reviews and a revision through durable RPC",
  {timeout: 20000},
  async () => {
    const before = new Set(peerEffects.keys());
    const result = await ingress()
      .client(peerReview, "release-note")
      .answer({brief: "Write a two-sentence release note about retries and journal replay."});
    assert.equal(result, "Revised answer.");
    // Two drafts and two reviews, each run exactly once despite forced replay.
    const added = [...peerEffects].filter(([key]) => !before.has(key));
    assert.equal(added.length, 4);
    assert.ok(added.every(([, count]) => count === 1));
  },
);

async function waitForApprovalCommand(service: string, key: string, after: number) {
  const target = `localhost:8080/${service}/${encodeURIComponent(key)}/approve`;
  for (let attempt = 0; attempt < 250; attempt++) {
    const command = approvalCommands.slice(after).find((line) => line.includes(target));
    if (command) return command;
    await delay(20);
  }
  throw new Error(`No approval command logged for ${target}`);
}

async function runApprovalCommand(command: string, approved: boolean) {
  // Execute the logged command itself, including shell quoting, against the test server.
  const {stdout} = await promisify(execFile)("/bin/sh", [
    "-c",
    command.replace("localhost:8080", env.baseUrl()).replace('"approved":true', `"approved":${approved}`),
  ]);
  assert.equal(JSON.parse(stdout), true);
}

for (const service of ["TicketApproval", "AiSession"]) {
  for (const approved of [true, false]) {
    void test(
      `${service}: logged approval command resolves decision ${approved}`,
      {timeout: 20000},
      async () => {
        const key = `decision ${approved}/bob's`;
        const after = approvalCommands.length;
        const reply = service === "TicketApproval"
          ? ingress().client(ticketApproval, key).ask({message: "Close ticket T-42."})
          : ingress().client(aiSession, key).doTurn({message: "approve ticket"});
        const [result] = await Promise.all([
          reply,
          (async () => {
            const command = await waitForApprovalCommand(service, key, after);
            await runApprovalCommand(command, approved);
          })(),
        ]);
        assert.equal(result, approved ? "Ticket T-42 is closed." : "Approval denied; ticket T-42 was left unchanged.");
      },
    );
  }
}

void test("human approval: an old command cannot approve a new invocation", {timeout: 20000}, async () => {
  const key = "stale-approval";
  const client = ingress().client(ticketApproval, key);
  let previousCommand = "";
  for (let turn = 0; turn < 2; turn++) {
    const after = approvalCommands.length;
    const [reply] = await Promise.all([
      client.ask({message: "Close ticket T-42."}),
      (async () => {
        const command = await waitForApprovalCommand("TicketApproval", key, after);
        if (previousCommand) await runApprovalCommand(previousCommand, true);
        await runApprovalCommand(command, false);
        previousCommand = command;
      })(),
    ]);
    assert.equal(reply, "Approval denied; ticket T-42 was left unchanged.");
  }
});

void test("support session returns only its reply while retaining conversation history", async () => {
  const client = connect({url: env.baseUrl()}).client(aiSession, "replies");
  const first = await client.doTurn({message: "Hello"});
  assert.equal(first, "Session answer; previous turns: 0");
  const second = await client.doTurn({message: "Another question"});
  assert.equal(second, "Session answer; previous turns: 1");
  const history = await client.history();
  assert.deepEqual(history.messages, [
    {role: "user", content: "Hello"},
    {role: "assistant", content: first},
    {role: "user", content: "Another question"},
    {role: "assistant", content: second},
  ]);
});

void test("interrupted support session returns its final summary", {timeout: 20000}, async () => {
  const client = connect({url: env.baseUrl()}).client(aiSession, "interrupted");
  assert.equal(await client.doTurn({message: "interrupt"}), "Stopped as requested.");
  assert.equal((await client.status()).active, null);
});

void test(
  "research plans typed work, runs RPC workers in parallel, cites sources, and replays effects once",
  {timeout: 20000},
  async () => {
    const before = new Set(effects.keys());
    const result = await connect({url: env.baseUrl()})
      .client(researchReport)
      .generate({topic: "Reliable execution", sources});
    assert.match(result, /\[durability\]/);
    assert.match(result, /\[idempotency\]/);
    const added = [...effects].filter(([key]) => !before.has(key));
    assert.equal(added.length, 6);
    assert.ok(added.every(([, count]) => count === 1));
  },
);

void test("research rejects duplicate source IDs before invoking a model", async () => {
  const calls = effects.size;
  await assert.rejects(
    connect({url: env.baseUrl()})
      .client(researchReport)
      .generate({topic: "Invalid catalog", sources: [sources[0], sources[0]]}),
    /Source IDs must be unique/,
  );
  assert.equal(effects.size, calls);
});

void test("a research worker that cites a source it has not read must read it first", async () => {
  const finding = await connect({url: env.baseUrl()})
    .client(researchWorker)
    .research({question: "cite without reading", sources});
  assert.deepEqual(finding, {answer: "Supported claim", sourceIds: ["durability"]});
});

void test(`${codeReview.name}: evaluator feedback reaches the next draft and stops on acceptance`, async () => {
  const task = "Read the first item safely";
  const before = reviewCounts.get(task) ?? 0;
  const result = await ingress().client(codeReview, "accepted").generate({task});
  assert.equal(result, "return items.length ? items[0] : undefined;");
  assert.equal(reviewCounts.get(task)! - before, 2);
});

void test(`${codeReview.name}: exhausting the budget retains the last draft and feedback`, async () => {
  const task = "always reject";
  const before = reviewCounts.get(task) ?? 0;
  const result = await ingress().client(codeReview, "rejected").generate({task});
  assert.match(result, /still needs work after 3 reviews: Handle empty input/);
  assert.match(result, /items.length/);
  assert.equal(reviewCounts.get(task)! - before, 3);
});

void test(
  "racing returns the winner only after the losing agent's cleanup",
  {timeout: 20000},
  async () => {
    const before = cleanedRaces.size;
    const result = await connect({url: env.baseUrl()})
      .client(racingAgents)
      .answer({question: "cancel loser"});
    assert.equal(result, "Quick answer");
    assert.equal(cleanedRaces.size - before, 1);
  },
);

for (const question of ["fallback", "stopped quick"]) {
  void test(`racing waits for a completed answer after ${question}`, {timeout: 20000}, async () => {
    assert.equal(
      await connect({url: env.baseUrl()}).client(racingAgents).answer({question}),
      "Thorough answer",
    );
  });
}
void test("racing fails clearly if neither agent completes", async () => {
  await assert.rejects(
    connect({url: env.baseUrl()}).client(racingAgents).answer({question: "both fail"}),
    /Neither candidate produced a completed answer/,
  );
});

void test(
  "16: a subscriber receives the audit's next progress event",
  {timeout: 30000},
  async () => {
    const subscriber = ingress().client(progressFeed, "audit-test").subscribe();
    // Start the audit only once the subscriber is registered.
    const feed = env.stateOf(progressFeed, "audit-test");
    while (!(await feed.get<string[]>("subscribers"))?.length) await delay(50);
    const reply = await ingress()
      .client(inventoryAudit)
      .audit({job: "audit-test", request: "Count stock in Berlin and Oslo."});
    assert.equal(reply, "Oslo has the least stock.");
    assert.deepEqual(await subscriber, {type: "step", step: 1});
  },
);

void test("string prompt defaults are exposed as object fields for the request editor", async () => {
  const response = await fetch(`${env.adminAPIBaseUrl()}/services`);
  assert.ok(response.ok);
  const {services} = await response.json() as {services: {
    name: string;
    handlers: {name: string; input_json_schema: {
      type: string;
      properties: Record<string, {type: string; default?: unknown; minLength?: number}>;
    }}[];
  }[]};
  for (const [service, handler, field] of [
    ["Hello", "ask", "message"],
    ["TicketLookup", "ask", "message"],
    ["ChatSession", "ask", "message"],
    ["TicketTriage", "classify", "message"],
    ["TicketApproval", "ask", "message"],
    ["SupportRouter", "answer", "question"],
    ["PeerReview", "answer", "brief"],
    ["AiSession", "steer", "message"],
    ["AiSession", "interrupt", "reason"],
    ["SkilledWriter", "write", "request"],
    ["IncidentInvestigation", "investigate", "incident"],
  ]) {
    const schema = services.find((item) => item.name === service)!
      .handlers.find((item) => item.name === handler)!.input_json_schema;
    assert.equal(schema.type, "object");
    assert.equal(schema.properties[field].type, "string");
    assert.equal(typeof schema.properties[field].default, "string");
    assert.equal(schema.properties[field].minLength, undefined);
  }
  const reply = await fetch(`${env.baseUrl()}/Hello/ask`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: "{}",
  });
  assert.ok(reply.ok);
  assert.equal(await reply.json(), "Say hello in one sentence.");
});

void test("19: the agent loads a skill from the folder and reads its file", async () => {
  const notes = await ingress().client(skilledWriter).write({request: "Release notes for 2.4.0"});
  assert.equal(notes, "## <version> — <date>");
});

void test("20: forks start from the investigator's conversation and cannot start forks", async () => {
  const report = await ingress()
    .client(incidentInvestigation, "checkout-502")
    .investigate({incident: "Checkout returns 502 errors since 12:00."});
  assert.equal(
    report,
    "Payments v2.3.0. Supported: the pool ran out two minutes after the deploy. " +
      "Rejected: inventory answers within 80ms.",
  );
});
