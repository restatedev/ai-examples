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
import { zodPrompt } from "./utils/utils";

const examplePrompt =
  "Our Q3 results exceeded all expectations! Customer satisfaction reached 95%, revenue grew " +
  "by 40% year-over-year, and we successfully launched three new product features. " +
  "The team worked incredibly hard to deliver these outcomes despite supply chain challenges. " +
  "Our market share increased to 23%, and we're well-positioned for continued growth in Q4.";

// <start_here>
async function analyze(ctx: Context, { message }: { message: string }) {
  // Create parallel tasks - each runs independently
  const tasks = [
    ctx.run(
      "Analyze sentiment",
      // Use your preferred LLM SDK here
      async () => llmCall(`Analyze sentiment: ${message}`),
      { maxRetryAttempts: 3 },
    ),
    ctx.run(
      "Extract key points",
      async () => llmCall(`Extract 3 key points as bullets: ${message}`),
      { maxRetryAttempts: 3 },
    ),
    ctx.run(
      "Summarize",
      async () => llmCall(`Summarize in one sentence: ${message}`),
      { maxRetryAttempts: 3 },
    ),
  ];

  // Wait for all tasks to complete and return the results
  const results = await RestatePromise.all(tasks);
  return results.map((res) => res.text);
}
// <end_here>

export default restate.service({
  name: "ParallelAgentsService",
  handlers: {
    analyze: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      analyze,
    ),
  },
});
