import { agent, asyncTool } from "@restatedev/agentlib";
import { openAIModel } from "@restatedev/agentlib/openai";
import * as restate from "@restatedev/restate-sdk-gen";
import { z } from "zod";

const weatherAgent = agent({
  model: openAIModel({
    model: process.env.AGENT_MODEL ?? "gpt-5.4",
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

export const weatherService = restate.service({
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
        const result = yield* weatherAgent.run(prompt);
        return result.status === "completed" ? result.output : result.output ?? result.reason;
      },
    ),
  },
});
