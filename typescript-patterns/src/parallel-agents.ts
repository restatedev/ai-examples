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

async function analyzeText(
  ctx: Context,
  { message }: { message: string },
): Promise<string[]> {
  // Create parallel tasks - each runs independently
  const tasks = [
    ctx.run(
      "Analyze sentiment",
      async () =>
        llmCall(`Analyze sentiment (positive/negative/neutral): ${message}`),
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
  return RestatePromise.all(tasks);
}

export default restate.service({
  name: "ParallelAgentsService",
  handlers: {
    analyzeText: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      analyzeText,
    ),
  },
});
