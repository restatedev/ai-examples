import * as restate from "@restatedev/restate-sdk";
import { RestatePromise } from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import {generateText, Output, wrapLanguageModel} from "ai";
import { durableCalls } from "@restatedev/vercel-ai-middleware";
import { ResearchRequestSchema, ResearchRequest } from "./utils/types";
import { z } from "zod";
const schema = restate.serde.schema;

// <start_here>
export const researchWorker = restate.service({
  name: "ResearchWorker",
  handlers: {
    research: async (ctx: restate.Context, {question}: { question: string }) => {
      const model = wrapLanguageModel({
        model: openai("gpt-4o"),
        middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
      });
      const { text: answer } = await generateText({
        model,
        system:
          "You are a research assistant. Provide a concise, factual answer.",
        prompt: question,
      });
      return { question, answer };
    },
  },
});

const orchestrator = restate.service({
  name: "ResearchReport",
  handlers: {
    generate: restate.createServiceHandler(
      { input: schema(ResearchRequestSchema) },
      async (ctx: restate.Context, {topic}: { topic: string }) => {
        const model = wrapLanguageModel({
          model: openai("gpt-4o"),
          middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
        });

        // Step 1: Orchestrator creates a research plan
        const { output: tasks } = await generateText({
          model,
          system: `You are a research planner. Break the topic into 2-4 research
          sub-tasks. Respond with a JSON array of strings, each a specific
          research question. Example: ["question 1", "question 2"]`,
          prompt: topic,
          output: Output.array({element: z.string()})
        });

        // Step 2: Dispatch workers in parallel
        const workerResults = await RestatePromise.all(
          tasks.map((question) =>
            ctx.serviceClient(researchWorker).research({ question }),
          ),
        );

        // Step 3: Combine results into a report
        const { text: report } = await generateText({
          model,
          system:
            "You are a report writer. Combine the research findings into a cohesive report.",
          prompt: `Topic: ${topic}\n\nResearch findings:\n${JSON.stringify(workerResults)}`,
        });

        return { report, taskCount: tasks.length };
      },
    ),
  },
});
// <end_here>

restate.serve({ services: [orchestrator, researchWorker] });
