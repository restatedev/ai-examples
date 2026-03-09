/**
 * Evaluator-Optimizer Pattern
 *
 * Generate → Evaluate → Improve loop until quality criteria are met.
 * Restate persists each iteration, resuming from the last completed step on failure.
 */
import * as restate from "@restatedev/restate-sdk";
import llmCall from "./utils/llm";
import {CodeGenRequestSchema} from "./utils/utils";
const schema = restate.serde.schema;

// <start_here>
const generate = async (ctx: restate.Context, {task}: { task: string }) => {
    let feedback = "";
    const maxIterations = 3;

    for (let i = 0; i < maxIterations; i++) {
      // Step 1: Generate code
      const code = await ctx.run(
        `Generate code (attempt ${i + 1})`,
        async () =>
          llmCall(
            feedback
              ? `You are a code generator. Write clean, correct code.\n\nTask: ${task}\n\nPrevious attempt was rejected:\n${feedback}\n\nPlease fix the issues.`
              : `You are a code generator. Write clean, correct code.\n\nTask: ${task}`,
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
            or FAIL: <feedback> with specific issues to fix.\n\nTask: ${task}\n\nCode:\n${code.text}`,
          ),
        { maxRetryAttempts: 3 },
      );

      if (evaluation.text.startsWith("PASS")) {
        return { code: code.text, iterations: i + 1 };
      }

      feedback = evaluation.text;
    }

    return { code: "Max iterations reached", iterations: maxIterations };
};

const agent = restate.service({
  name: "CodeGenerator",
  handlers: {
    generate: restate.createServiceHandler(
        { input: schema(CodeGenRequestSchema) },
        generate,
    ),
  },
});
// <end_here>

restate.serve({ services: [agent], port: 9080 });
