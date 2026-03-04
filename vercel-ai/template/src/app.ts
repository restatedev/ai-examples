import * as restate from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, stepCountIs, tool, wrapLanguageModel } from "ai";
import { z } from "zod";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
const schema = restate.serde.schema;

export const WeatherPromptSchema = z.object({
  prompt: z.string().default("What is the weather like in San Francisco?"),
});
export type WeatherPrompt = z.infer<typeof WeatherPromptSchema>;

// TOOL
async function getWeather(ctx: restate.Context, city: string) {
  // Do durable steps using the Restate context
  return ctx.run(`get weather ${city}`, () => {
    // Simulate calling the weather API
    return {temperature: 23, description: `Sunny and warm.`}
  })
}

// AGENT
const run = async (ctx: restate.Context, { prompt }: WeatherPrompt) => {
  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    // Persist LLM responses
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
        execute: async ({ city }) => getWeather(ctx, city),
      }),
    },
    stopWhen: [stepCountIs(5)],
    providerOptions: { openai: { parallelToolCalls: false } },
  });

  return text;
};

// AGENT SERVICE
const agent = restate.service({
  name: "agent",
  handlers: {
    run: restate.createServiceHandler({ input: schema(WeatherPromptSchema) }, run),
  },
});

restate.serve({ services: [agent] });
