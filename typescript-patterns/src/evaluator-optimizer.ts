/**
 * Evaluator-Optimizer Pattern
 *
 * Generate → Evaluate → Improve loop until quality criteria are met.
 * Restate persists each iteration, resuming from the last completed step on failure.
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
async function run(ctx: Context, { message }: { message: string }) {
  let solution: string | null = null;
  const attempts: string[] = [];

  for (let i = 0; i < maxIterations; i++) {
    // Generate solution (with context from previous attempts)
    const taskPrompt = `Task: ${message} - Previous attempts: ${attempts.join(", ")}`;
    const solution = await ctx.run(
      `Generate v${i}`,
      // Use your preferred LLM SDK here
      async () => llmCall(taskPrompt).then((res) => res.text),
      { maxRetryAttempts: 3 },
    );
    attempts.push(solution);

    // Evaluate the solution
    const evalPrompt = `${evaluationPrompt} Task: ${message} - Solution: ${solution}`;
    const evaluation = await ctx.run(
      `Evaluate v${i}`,
      async () => llmCall(evalPrompt).then((res) => res.text),
      { maxRetryAttempts: 3 },
    );
    printEvaluation(i, solution, evaluation);

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
    run: restate.createServiceHandler({ input: zodPrompt(examplePrompt) }, run),
  },
});
