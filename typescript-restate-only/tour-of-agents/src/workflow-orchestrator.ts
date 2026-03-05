/**
 * Orchestrator-Worker Pattern
 *
 * Break down complex tasks into specialized subtasks and execute them in parallel.
 * If any worker fails, Restate retries only that worker while preserving other completed work.
 */
import * as restate from "@restatedev/restate-sdk";
import { RestatePromise } from "@restatedev/restate-sdk";
import llmCall from "./utils/llm";

// <start_here>
export const researchWorker = restate.service({
  name: "ResearchWorker",
  handlers: {
    research: async (ctx: restate.Context, req: { question: string }) => {
      const answer = await ctx.run(
        "Research",
        async () =>
          llmCall(
            `You are a research assistant. Provide a concise, factual answer.\n\n${req.question}`,
          ),
        { maxRetryAttempts: 3 },
      );
      return { question: req.question, answer: answer.text };
    },
  },
});

const orchestrator = restate.service({
  name: "ResearchReport",
  handlers: {
    generate: async (ctx: restate.Context, req: { topic: string }) => {
      // Step 1: Orchestrator creates a research plan
      const planJson = await ctx.run(
        "Create research plan",
        async () =>
          llmCall(
            `You are a research planner. Break the topic into 2-4 research
          sub-tasks. Respond with a JSON array of strings, each a specific
          research question. Example: ["question 1", "question 2"]\n\nTopic: ${req.topic}`,
          ),
        { maxRetryAttempts: 3 },
      );
      const tasks: string[] = JSON.parse(planJson.text);

      // Step 2: Dispatch workers in parallel
      const workerResults = await RestatePromise.all(
        tasks.map((question) =>
          ctx.serviceClient(researchWorker).research({ question }),
        ),
      );

      // Step 3: Combine results into a report
      const report = await ctx.run(
        "Write report",
        async () =>
          llmCall(
            `You are a report writer. Combine the research findings into a cohesive report.\n\nTopic: ${req.topic}\n\nResearch findings:\n${JSON.stringify(workerResults, null, 2)}`,
          ),
        { maxRetryAttempts: 3 },
      );

      return { report: report.text, taskCount: tasks.length };
    },
  },
});
// <end_here>

restate.serve({ services: [orchestrator, researchWorker], port: 9080 });
