import * as restate from "@restatedev/restate-sdk";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
import { openai } from "@ai-sdk/openai";
import { generateText, stepCountIs, tool, wrapLanguageModel } from "ai";
import { z } from "zod";

// TOOL
async function getWeather(ctx: restate.Context, city: string) {
  // Do durable steps using the Restate context
  return ctx.run(`get weather ${city}`, () => {
    // Simulate calling the weather API
    return {temperature: 23, description: `Sunny and warm.`}
  })
}

// AGENT
const run = async (ctx: restate.Context, { prompt }: { prompt: string }) => {
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
    run: restate.createServiceHandler({
      input: restate.serde.schema(z.object({
        prompt: z.string().default("What's the weather in San Francisco?"),
      })),
    }, run),
  },
});

restate.serve({ services: [agent] });
