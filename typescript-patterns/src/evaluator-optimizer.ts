/**
 * Evaluator-Optimizer Pattern
 *
 * Generate → Evaluate → Improve loop until quality criteria are met.
 * Restate persists each iteration, resuming from the last completed step on failure.
 *
 * Generate � Evaluate � [Pass/Improve] � Final Result
 */
import * as restate from "@restatedev/restate-sdk";
import { Context } from "@restatedev/restate-sdk";
import llmCall from "./utils/llm";
import { printEvaluation, zodPrompt } from "./utils/utils";

const maxIterations = 5;
const examplePrompt =
  "Write a Python function that finds the longest palindromic substring in a string. " +
  "It should be efficient and handle edge cases.";
const evaluationPrompt =
  `Evaluate this solution on correctness, efficiency, and readability. Reply with: ` +
  `'PASS: [brief reason]' if the solution is correct and very well-implemented ` +
  `'IMPROVE: [specific issues to fix]' if it needs work. `;

// <start_here>
async function improveUntilGood(
  ctx: Context,
  { message }: { message: string },
): Promise<string> {
  let solution: string | null = null;
  const attempts: string[] = [];

  for (let iteration = 0; iteration < maxIterations; iteration++) {
    // Generate solution (with context from previous attempts)
    solution = await ctx.run(
      `generate_v${iteration + 1}`,
      async () =>
        llmCall(`Task: ${message} - Previous attempts: ${attempts.join(", ")}`),
      { maxRetryAttempts: 3 },
    );
    if (solution) {
      attempts.push(solution);
    }

    // Evaluate the solution
    const evaluation = await ctx.run(
      `evaluate_v${iteration + 1}`,
      async () =>
        llmCall(`${evaluationPrompt} Task: ${message} - Solution: ${solution}`),
      { maxRetryAttempts: 3 },
    );
    printEvaluation(iteration, solution, evaluation);

    if (evaluation && evaluation.startsWith("PASS")) {
      return solution;
    }
  }

  return `Max iterations reached. Best attempt:\n${solution}`;
}
// <end_here>

export default restate.service({
  name: "EvaluatorOptimizer",
  handlers: {
    improveUntilGood: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      improveUntilGood,
    ),
  },
});
