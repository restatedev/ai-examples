// 15: Exchange drafts and feedback between agents through typed Restate RPCs.
import {TerminalError} from "@restatedev/restate-sdk";
import * as restate from "@restatedev/restate-sdk-gen";
import {agent, Conversation} from "@restatedev/agentlib";
import {z} from "zod";
import {openai} from "@ai-sdk/openai";
import {aiModel} from "@restatedev/agentlib/provider";

const model = aiModel({model: openai(process.env.AGENT_MODEL ?? "gpt-5.4")});

const brief = z.string().max(4000);
const draft = z.string().max(12000);
const reviewFocuses = ["requirements", "clarity"] as const;
const focus = z.enum(reviewFocuses);

const author = agent({
  model,
  maxSteps: 2,
  instructions:
    "Write a concise answer using only facts in the brief. When you receive review feedback, revise your draft to address every review.",
});
const reviewer = agent({
  model,
  maxSteps: 2,
  instructions:
    "Review the draft for the requested focus only. Return one short, actionable suggestion. Check requirements against the brief; do not invent outside facts.",
});

/** One author per review. Its conversation keeps the brief and the first draft for the revision. */
export const peerAuthor = restate.object({
  name: "PeerAuthor",
  handlers: {
    write: restate.schemas({input: z.object({brief}), output: draft}, function* (request) {
      const result = yield* author.run(request.brief, {
        name: "first-draft",
        conversation: new Conversation(),
      });
      if (result.status !== "completed")
        throw new TerminalError(`Author ${result.status}: ${result.reason}`);
      return result.output;
    }),
    revise: restate.schemas(
      {input: z.object({feedback: z.array(z.string().max(2000)).max(2)}), output: draft},
      function* ({feedback}) {
        const result = yield* author.run(
          `Revise your draft to address this feedback:\n${feedback.join("\n")}`,
          {name: "revision", conversation: new Conversation()},
        );
        if (result.status !== "completed")
          throw new TerminalError(`Author ${result.status}: ${result.reason}`);
        return result.output;
      },
    ),
  },
  options: {state: {preload: ["conversation/meta", "conversation/summary"]}},
});

/** One reviewer per review and focus, so the two reviews run in parallel. */
export const peerReviewer = restate.object({
  name: "PeerReviewer",
  handlers: {
    review: restate.schemas(
      {input: z.object({brief, draft, focus}), output: z.string().max(2000)},
      function* (request) {
        const result = yield* reviewer.run(JSON.stringify(request), {
          name: `review-${request.focus}`,
          conversation: new Conversation(),
        });
        if (result.status !== "completed")
          throw new TerminalError(`Reviewer ${result.status}: ${result.reason}`);
        return result.output;
      },
    ),
  },
  options: {state: {preload: ["conversation/meta", "conversation/summary"]}},
});

/** One object per review. Its key also names the review's author and reviewers. */
export const peerReview = restate.object({
  name: "PeerReview",
  handlers: {
    answer: restate.schemas(
      {
        input: z.object({
          brief: brief.default("Write a two-sentence release note for a feature that retries transient failures and resumes completed steps from a journal."),
        }),
        output: draft,
      },
      function* ({brief: request}) {
        const key = restate.handlerRequest().key!;
        const writer = restate.client(peerAuthor, key);
        const firstDraft = yield* writer.write({brief: request});
        const comments = yield* restate.all(
          reviewFocuses.map((focus) =>
            restate
              .client(peerReviewer, `${key}/${focus}`)
              .review({brief: request, draft: firstDraft, focus}),
          ),
        );
        const feedback = comments.map((comment, index) => `${reviewFocuses[index]}: ${comment}`);
        return yield* writer.revise({feedback});
      },
    ),
  },
});
