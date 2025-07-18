import * as restate from "@restatedev/restate-sdk";
import { durableCalls, toolErrorAsTerminalError } from "@restatedev/vercel-ai-middleware"
import { openai } from "@ai-sdk/openai";
import { generateText, tool, wrapLanguageModel } from "ai";
import { z } from "zod";
import { fetchWeather } from "./utils/weather";


// --------------------------------------------------------
//  A simple agent, following the template of the AI SDK
//  tool calling examples
// --------------------------------------------------------

async function simpleAgent(restate: restate.Context, prompt: string) {

  // we wrap the model with the 'durableCalls' middleware, which
  // stores each response in Restate's journal, to be restored on retries
  const model = wrapLanguageModel({
    model: openai("gpt-4o-2024-08-06", { structuredOutputs: true }),
    middleware: durableCalls(restate, { maxRetryAttempts: 3 }),
  });

  const result = await generateText({
    model,
    tools: {
      getWeather: tool({
        description: "Get the current weather for a given city.",
        parameters: z.object({ city: z.string() }),
        execute: async ({ city }) => {
          // call tool wrapped as Restate durable step
          return await restate.run("get weather", () => fetchWeather(city));
        }
      })
    },
    maxSteps: 5,
    // these are local retries by the AI SDK
    // Restate will retry the invocation once those local retries are exhaused to
    // handle longer downtimes, faulty processes, or network communication issues
    maxRetries: 3,
    system: "You are a helpful agent.",
    messages: [{ role: "user", content: prompt }]
  });

  return result.text;

}

// create a simple Restate service as the callable entrypoint
// for our durable agent function
const agent = restate.service({
  name: "agent",
  handlers: {
    run: async (ctx: restate.Context, prompt: string) => {
      return simpleAgent(ctx, prompt);
    },
  },
  options: {
    journalRetention: { days: 1 }, // keep the journal for 1 day, so that you can inspect what your agent did
    ...toolErrorAsTerminalError, // The ai sdk wraps tool errors with an ToolExecutionError, this will unwrap any TerminalError's wrapped in a ToolExecutionError
  },
});

// we serve the entry-point via an HTTP/2 server
restate.endpoint()
  .bind(agent)
  .listen(9080);
