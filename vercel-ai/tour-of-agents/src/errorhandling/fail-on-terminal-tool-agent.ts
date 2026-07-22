import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, stepCountIs, tool, wrapLanguageModel } from "ai";
import { z } from "zod";
import { fetchWeather } from "../utils/utils";
import {
  durableCalls, hasTerminalToolError,
  rethrowTerminalToolError,
} from "@restatedev/vercel-ai-middleware";

const agent = restate.service({
  name: "FailOnTerminalErrorAgent",
  handlers: {
    run: async (ctx: restate.Context, prompt: string) => {
      // <start_max_attempts_example>
      const model = wrapLanguageModel({
        model: openai("gpt-5.4"),
        middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
      });
      // <end_max_attempts_example>

      // Rethrow terminal tool errors as exceptions to fail the workflow
      // <start_option2>
      const { text, steps } = await generateText({
        model,
        tools: {
          getWeather: tool({
            description: "Get the current weather for a given city.",
            inputSchema: z.object({ city: z.string() }),
            execute: async ({ city }) => {
              return await ctx.run("get weather", () => fetchWeather(city), {maxRetryAttempts: 1});
            },
          }),
        },
        stopWhen: [stepCountIs(5), hasTerminalToolError],
        system: "You are a helpful agent that provides weather updates.",
        messages: [{ role: "user", content: prompt }],
      });


      for (const step of steps) {
        rethrowTerminalToolError(step);
      }
      // <end_option2>

      return text;
    },
  },
});

restate.serve({ services: [agent] });
