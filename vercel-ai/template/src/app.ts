import * as restate from "@restatedev/restate-sdk";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
import { openai } from "@ai-sdk/openai";
import { generateText, tool, wrapLanguageModel, stepCountIs } from "ai";
import { z } from "zod";
import { fetchWeather } from "./utils/weather";

// --------------------------------------------------------
//  A durable weather agent with Restate + Vercel AI SDK
// --------------------------------------------------------

async function simpleAgent(restate: restate.Context, prompt: string) {
  // we wrap the model with the 'durableCalls' middleware, which
  // stores each response in Restate's journal, to be restored on retries
  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(restate, { maxRetryAttempts: 3 }),
  });

  const { text } = await generateText({
    model,
    prompt,
    tools: {
      getWeather: tool({
        description: "Get the current weather for a given city.",
        inputSchema: z.object({ city: z.string() }),
        execute: async ({ city }) => {
          // call tool wrapped as Restate durable step
          return await restate.run("get weather", () => fetchWeather(city));
        },
      }),
    },
    stopWhen: [stepCountIs(5)],
    system: "You are a helpful agent.",
    providerOptions: { openai: { parallelToolCalls: false } },
  });

  return text;
}

// create a Restate Service as the callable entrypoint
// for our durable agent function
const agent = restate.service({
  name: "agent",
  handlers: {
    run: async (ctx: restate.Context, prompt: string) => {
      return simpleAgent(ctx, prompt);
    },
  },
});

// Serve the entry-point via an HTTP/2 server
restate.serve({
  services: [agent],
});
