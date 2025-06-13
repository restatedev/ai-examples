import * as restate from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";

import { openai } from "@ai-sdk/openai";
import { generateText, tool, wrapLanguageModel } from "ai";
import { z } from "zod";
import { durableCalls } from "./utils/ai_infra";

const agent = restate.service({
  name: "Agent",
  handlers: {
    run: restate.handlers.handler(
      { input: serde.zod(z.string()) },
      async (ctx: restate.Context, prompt) => {

        const model = wrapLanguageModel({
          model: openai("gpt-4o-2024-08-06", { structuredOutputs: true }),
          // Persist the results of LLM calls via the durableCalls middleware
          middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
        });

        const result = await generateText({
          model,
          system: "You are a helpful agent.",
          messages: [{ role: "user", content: prompt }],
          tools: {
            getWeather: tool({
              description: "Get the current weather for a given city.",
              parameters: z.object({ city: z.string() }),
              execute: async ({ city }) => {
                // implement durable tool steps using the Restate context
                return ctx.run("get weather", () => getWeather(ctx, city));
              },
            }),
          },
          maxRetries: 0,
          maxSteps: 10,
        });

        return result.text;
      },
    ),
  },
});

restate.endpoint().bind(agent).listen(9080);

// Utils

type WeatherResponse = {
  current_condition: {
    temp_C: string;
    weatherDesc: { value: string }[];
  }[];
};

async function getWeather(ctx: restate.Context, city: string) {
  const url = `https://wttr.in/${encodeURIComponent(city)}?format=j1`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed calling weather API: ${res.status}`);
  const data = (await res.json()) as WeatherResponse;
  const { temp_C, weatherDesc } = data.current_condition[0];
  return `Weather in ${city}: ${temp_C}°C, ${weatherDesc[0].value}`;
}
