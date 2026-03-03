import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, stepCountIs, tool, wrapLanguageModel } from "ai";
import { z } from "zod";
import { fetchWeather } from "./utils/utils";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
import {WeatherPrompt, WeatherPromptSchema} from "./utils/types";
const schema = restate.serde.schema;

const run = async (ctx: restate.Context, { prompt }: WeatherPrompt) => {
  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  const { text } = await generateText({
    model,
    system: "You are a helpful agent that provides weather updates.",
    prompt,
    tools: {
      getWeather: tool({
        description: "Get the current weather for a given city.",
        inputSchema: z.object({ city: z.string() }),
        execute: async ({ city }) =>
          ctx.run("get weather", () => fetchWeather(city)),
      }),
    },
    stopWhen: [stepCountIs(5)],
    providerOptions: { openai: { parallelToolCalls: false } },
  });

  return text;
};

const agent = restate.service({
  name: "WeatherAgent",
  handlers: {
    run: restate.createServiceHandler({ input: schema(WeatherPromptSchema), output: schema(z.string()) }, run),
  },
});

restate.serve({ services: [agent] });
