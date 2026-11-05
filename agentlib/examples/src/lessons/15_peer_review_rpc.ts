// 15: Exchange drafts and feedback between agents through typed Restate RPCs.
import {TerminalError} from "@restatedev/restate-sdk";
import * as restate from "@restatedev/restate-sdk-gen";
import {agent} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

const brief = z.string().max(4000);
const draft = z.string().max(12000);
const reviewFocuses = ["requirements", "clarity"] as const;
const focus = z.enum(reviewFocuses);

const author = agent({
  model,
  maxSteps: 2,
  instructions:
    "Write a concise answer using only facts in the brief. When a draft and feedback are supplied, revise that draft to address both reviews.",
});
const reviewer = agent({
  model,
  maxSteps: 2,
  instructions:
    "Review the draft for the requested focus only. Return one short, actionable suggestion. Check requirements against the brief; do not invent outside facts.",
});

export const peerAuthor = restate.service({
  name: "PeerAuthor",
  handlers: {
    write: restate.schemas(
      {
        input: z.object({
          brief,
          draft: draft.optional(),
          feedback: z.array(z.string().max(2000)).max(2),
        }),
        output: draft,
      },
      function* (request) {
        const name = request.draft ? "revision" : "first-draft";
        const result = yield* author.run(JSON.stringify(request), {name});
        if (result.status !== "completed")
          throw new TerminalError(`Author ${result.status}: ${result.reason}`);
        return result.output;
      },
    ),
  },
});

export const peerReviewer = restate.service({
  name: "PeerReviewer",
  handlers: {
    review: restate.schemas(
      {input: z.object({brief, draft, focus}), output: z.string().max(2000)},
      function* (request) {
        const result = yield* reviewer.run(JSON.stringify(request), {
          name: `review-${request.focus}`,
        });
        if (result.status !== "completed")
          throw new TerminalError(`Reviewer ${result.status}: ${result.reason}`);
        return result.output;
      },
    ),
  },
});

export const peerReview = restate.service({
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
        const firstDraft = yield* restate.client(peerAuthor).write({brief: request, feedback: []});
        const comments = yield* restate.all(
          reviewFocuses.map((focus) =>
            restate.client(peerReviewer).review({brief: request, draft: firstDraft, focus}),
          ),
        );
        const feedback = comments.map((comment, index) => `${reviewFocuses[index]}: ${comment}`);
        return yield* restate
          .client(peerAuthor)
          .write({brief: request, draft: firstDraft, feedback});
      },
    ),
  },
});
