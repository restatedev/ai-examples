import { Context } from "@restatedev/restate-sdk";
import { tool } from "ai";
import { z } from "zod";
import * as mathjs from "mathjs";
import { superJson } from "@restatedev/vercel-ai-middleware";

export const calculatorTool = (ctx: Context) =>
  tool({
    description:
      "A tool for evaluating mathematical expressions. " +
      "Example expressions: '1.2 * (2 + 4.5)', '12.7 cm to inch', 'sin(45 deg) ^ 2'.",
    inputSchema: z.object({ expression: z.string() }),
    execute: async ({ expression }) =>
      ctx.run(`evaluating ${expression}`, () => mathjs.evaluate(expression), {
        serde: superJson,
      }),
  });
