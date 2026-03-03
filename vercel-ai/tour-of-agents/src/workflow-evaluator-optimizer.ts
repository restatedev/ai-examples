import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, wrapLanguageModel } from "ai";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
import {CodeGenRequestSchema, CodeGenRequest} from "./utils/types";
const schema = restate.serde.schema;

// <start_here>
const generate = async (ctx: restate.Context, req: CodeGenRequest) => {
  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  let feedback = "";
  const maxIterations = 3;

  for (let i = 0; i < maxIterations; i++) {
    // Step 1: Generate code
    const { text: code } = await generateText({
      model,
      system: "You are a code generator. Write clean, correct code.",
      prompt: feedback
        ? `Task: ${req.task}\n\nPrevious attempt was rejected:\n${feedback}\n\nPlease fix the issues.`
        : `Task: ${req.task}`,
    });

    // Step 2: Evaluate the code
    const { text: evaluation } = await generateText({
      model,
      system: `You are a code reviewer. Evaluate the code for correctness,
            readability, and edge cases. Respond with PASS if acceptable,
            or FAIL: <feedback> with specific issues to fix.`,
      prompt: `Task: ${req.task}\n\nCode:\n${code}`,
    });

    if (evaluation.startsWith("PASS")) {
      return { code, iterations: i + 1 };
    }

    feedback = evaluation;
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

restate.serve({ services: [agent] });
