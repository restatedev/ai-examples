import { openai } from "@ai-sdk/openai";
import { agent, asyncTool, Conversation } from "@restatedev/agentlib";
import { aiModel } from "@restatedev/agentlib/provider";
import * as restate from "@restatedev/restate-sdk-gen";
import { z } from "zod";

const weatherAgent = agent({
  model: aiModel({
    model: openai(process.env.AGENT_MODEL ?? "gpt-5.4"),
    retry: { maxAttempts: 3 },
  }),
  instructions:
    "You provide weather updates. Use getWeather for each city requested and explain that the readings are demo data.",
  maxSteps: 5,
  tools: {
    getWeather: asyncTool({
      description: "Get demo weather for a city (not a live forecast).",
      input: z.object({ city: z.string().min(1) }),
      retry: { maxAttempts: 3 },
      async execute({ city }) {
        // Replace this mock with a weather API call. asyncTool journals the
        // result and applies the retry policy; no extra run wrapper is needed.
        return { city, temperature: 23, unit: "celsius", description: "Sunny and warm", demo: true };
      },
    }),
  },
});

// One virtual object per conversation: requests to the same key continue it.
export const weatherService = restate.object({
  name: "agent",
  handlers: {
    run: restate.schemas(
      {
        input: z.object({
          prompt: z.string().min(1).default("What's the weather in San Francisco?"),
        }),
        output: z.string(),
      },
      function* ({ prompt }) {
        // The run loads the conversation from this object's state and saves its progress there.
        const result = yield* weatherAgent.run(prompt, { conversation: new Conversation() });
        return result.status === "completed" ? result.output : result.output ?? result.reason;
      },
    ),
  },
  options: {
    // Restate sends these keys with each request. The run reads the message chunks on demand.
    state: { preload: ["conversation/meta", "conversation/summary"] },
  },
});
