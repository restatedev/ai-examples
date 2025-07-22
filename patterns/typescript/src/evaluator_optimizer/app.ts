import * as restate from "@restatedev/restate-sdk";
import { llmCall, extractXml } from "../util/utils";

export interface LoopRequest {
  task: string;
  evaluatorPrompt: string;
  generatorPrompt: string;
}

export const evaluatorOptimizer = restate.service({
  name: "EvaluatorOptimizer",
  handlers: {
    loop: async (
      ctx: restate.Context,
      req: LoopRequest,
    ): Promise<[string, Array<{ thoughts: string; result: string }>]> => {
      const [thoughts, result] = await generate(
        ctx,
        req.generatorPrompt,
        req.task,
      );
      const memory = [result];
      const chainOfThought = [{ thoughts, result }];

      while (true) {
        const [evaluation, feedback] = await evaluate(
          ctx,
          req.evaluatorPrompt,
          result,
          req.task,
        );

        if (evaluation === "PASS") {
          return [result, chainOfThought];
        }

        const llmContext = [
          "Previous attempts:",
          ...memory.map((m) => `- ${m}`),
          `\nFeedback: ${feedback}`,
        ].join("\n");

        const [newThoughts, newResult] = await generate(
          ctx,
          req.generatorPrompt,
          req.task,
          llmContext,
        );
        memory.push(newResult);
        chainOfThought.push({ thoughts: newThoughts, result: newResult });
      }
    },
  },
});

// UTILS
async function generate(
  ctx: restate.Context,
  prompt: string,
  task: string,
  llmContext: string = "",
): Promise<[string, string]> {
  const fullPrompt = llmContext
    ? `${prompt}\n${llmContext}\nTask: ${task}`
    : `${prompt}\nTask: ${task}`;

  const response = await ctx.run("LLM call", () => llmCall(fullPrompt));
  const thoughts = extractXml(response, "thoughts");
  const result = extractXml(response, "response");

  console.log("\n=== GENERATION START ===");
  console.log(`Thoughts:\n${thoughts}\n`);
  console.log(`Generated:\n${result}`);
  console.log("=== GENERATION END ===\n");

  return [thoughts, result];
}

async function evaluate(
  ctx: restate.Context,
  prompt: string,
  content: string,
  task: string,
): Promise<[string, string]> {
  const fullPrompt = `${prompt}\nOriginal task: ${task}\nContent to evaluate: ${content}`;
  const response = await ctx.run("LLM call", () => llmCall(fullPrompt));
  const evaluation = extractXml(response, "evaluation");
  const feedback = extractXml(response, "feedback");

  console.log("=== EVALUATION START ===");
  console.log(`Status: ${evaluation}`);
  console.log(`Feedback: ${feedback}`);
  console.log("=== EVALUATION END ===\n");

  return [evaluation, feedback];
}

export default evaluatorOptimizer;
