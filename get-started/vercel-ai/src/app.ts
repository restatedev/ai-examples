import * as restate from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";

import { openai } from "@ai-sdk/openai";
import { generateText, tool, wrapLanguageModel } from "ai";
import { z } from "zod";
import { durableCalls } from "./utils/ai_infra";
import { fetchWeather, parseWeatherResponse } from "./utils/utils";

// Durable tool workflow
const getWeatherTool = (restate_context: restate.Context) =>
  tool({
    description: "Get the current weather for a given city.",
    parameters: z.object({ city: z.string() }),
    execute: async ({ city }) => {
      const result = await restate_context.run("get weather", async () => fetchWeather(city));
      return await parseWeatherResponse(result);
    },
  });

const agent = restate.service({
  name: "Agent",
  handlers: {
    run: restate.handlers.handler(
      { input: serde.zod(z.string()) },
      async (ctx: restate.Context, prompt) => {
        // Persist the results of LLM calls via the durableCalls middleware
        const model = wrapLanguageModel({
          model: openai("gpt-4o-2024-08-06", { structuredOutputs: true }),
          middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
        });

        const result = await generateText({
          model,
          system: "You are a helpful agent.",
          messages: [{ role: "user", content: prompt }],
          tools: { getWeather: getWeatherTool(ctx) },
          maxRetries: 0,
          maxSteps: 10,
        });

        return result.text;
      },
    ),
  },
});

restate.endpoint().bind(agent).listen(9080);
