import * as restate from "@restatedev/restate-sdk";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
import { openai } from "@ai-sdk/openai";
import { generateText, tool, wrapLanguageModel, stepCountIs } from "ai";
import { z } from "zod";
import { fetchWeather } from "./utils/weather";

// --------------------------------------------------------
//  A durable weather agent with Restate + Vercel AI SDK
// --------------------------------------------------------

async function weatherAgent(restate: restate.Context, prompt: string) {
  // The durableCalls middleware persists each LLM response in Restate,
  // so they can be restored on retries without re-calling the LLM
  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(restate, { maxRetryAttempts: 3 }),
  });

  const { text } = await generateText({
    model,
    system: "You are a helpful agent that provides weather updates.",
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
      return weatherAgent(ctx, prompt);
    },
  },
});

// Serve the entry-point via an HTTP/2 server
restate.serve({
  services: [agent],
});
