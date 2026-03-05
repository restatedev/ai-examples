/**
 * Evaluator-Optimizer Pattern
 *
 * Generate → Evaluate → Improve loop until quality criteria are met.
 * Restate persists each iteration, resuming from the last completed step on failure.
 */
import * as restate from "@restatedev/restate-sdk";
import llmCall from "./utils/llm";

// <start_here>
const workflowEvaluatorOptimizer = restate.service({
  name: "CodeGenerator",
  handlers: {
    generate: async (ctx: restate.Context, req: { task: string }) => {
      let feedback = "";
      const maxIterations = 3;

      for (let i = 0; i < maxIterations; i++) {
        // Step 1: Generate code
        const code = await ctx.run(
          `Generate code (attempt ${i + 1})`,
          async () =>
            llmCall(
              feedback
                ? `You are a code generator. Write clean, correct code.\n\nTask: ${req.task}\n\nPrevious attempt was rejected:\n${feedback}\n\nPlease fix the issues.`
                : `You are a code generator. Write clean, correct code.\n\nTask: ${req.task}`,
            ),
          { maxRetryAttempts: 3 },
        );

        // Step 2: Evaluate the code
        const evaluation = await ctx.run(
          `Evaluate code (attempt ${i + 1})`,
          async () =>
            llmCall(
              `You are a code reviewer. Evaluate the code for correctness,
              readability, and edge cases. Respond with PASS if acceptable,
              or FAIL: <feedback> with specific issues to fix.\n\nTask: ${req.task}\n\nCode:\n${code.text}`,
            ),
          { maxRetryAttempts: 3 },
        );

        if (evaluation.text.startsWith("PASS")) {
          return { code: code.text, iterations: i + 1 };
        }

        feedback = evaluation.text;
      }

      return { code: "Max iterations reached", iterations: maxIterations };
    },
  },
});
// <end_here>

restate.serve({ services: [workflowEvaluatorOptimizer], port: 9080 });
