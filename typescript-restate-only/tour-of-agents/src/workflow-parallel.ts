/**
 * Parallel Agent Processing
 *
 * Process multiple inputs simultaneously with specialized agents.
 * If any task fails, Restate retries only the failed tasks while preserving completed results.
 *
 * Task A ↘
 * Task B → [Wait on Results] � Results A, B, C
 * Task C ↗
 */
import * as restate from "@restatedev/restate-sdk";
import { Context, RestatePromise } from "@restatedev/restate-sdk";
import llmCall from "./utils/llm";
import {ClaimInputSchema, ClaimInput} from "./utils/utils";
const schema = restate.serde.schema;

// <start_here>
async function analyze(ctx: Context, claim: ClaimInput) {
  // Create parallel tasks - each runs independently
  const claimJson = JSON.stringify(claim);
  const eligibility = ctx.run(
    "Eligibility agent",
    async () => llmCall(
        "Decide whether the following claim is eligible for reimbursement." +
        "Respond with eligible if it's a medical claim, and not eligible otherwise." +
        "\n\nClaim: " + claimJson,
    ),
    { maxRetryAttempts: 3 },
  )
  const fraud = ctx.run(
    "Fraud agent",
    async () => llmCall(
        "Decide whether the cost of the claim is reasonable given the treatment." +
        "Respond with reasonable or not reasonable." +
        "\n\nClaim: " + claimJson,
    ),
    { maxRetryAttempts: 3 },
  )
  const cost = ctx.run(
    "Rate comparison agent",
    async () => llmCall(
        "Decide whether the claim is fraudulent." +
        "Always respond with low risk, medium risk, or high risk." +
        "\n\nClaim: " + claimJson,
    ),
    { maxRetryAttempts: 3 },
  )

  // Wait for all tasks to complete and return the results
  await RestatePromise.all([eligibility, cost, fraud]);

  // Make final decision
  const { text } = await ctx.run(
      "Decision agent",
      async () => llmCall( `Decide about claim ${JSON.stringify(claim)}.
        Base your decision on the following analyses:
        Eligibility: ${eligibility}, Cost: ${cost} Fraud: ${fraud}`)
  );
  return text
}
// <end_here>

const workflowParallel = restate.service({
  name: "ParallelAgentsService",
  handlers: {
    analyze: restate.createServiceHandler(
      { input: schema(ClaimInputSchema) },
      analyze,
    ),
  },
});

restate.serve({ services: [workflowParallel], port: 9080 });
