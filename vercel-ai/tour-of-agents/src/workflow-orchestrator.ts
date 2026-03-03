import * as restate from "@restatedev/restate-sdk";
import { RestatePromise } from "@restatedev/restate-sdk";
import { openai } from "@ai-sdk/openai";
import { generateText, wrapLanguageModel } from "ai";
import { durableCalls } from "@restatedev/vercel-ai-middleware";

// <start_here>
const agent = restate.service({
  name: "ResearchReport",
  handlers: {
    generate: async (ctx: restate.Context, req: { topic: string }) => {
      const model = wrapLanguageModel({
        model: openai("gpt-4o"),
        middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
      });

      // Step 1: Orchestrator creates a research plan
      const { text: planJson } = await generateText({
        model,
        system: `You are a research planner. Break the topic into 2-4 research
          sub-tasks. Respond with a JSON array of strings, each a specific
          research question. Example: ["question 1", "question 2"]`,
        prompt: req.topic,
      });
      const tasks: string[] = JSON.parse(planJson);

      // Step 2: Dispatch workers in parallel
      const workerResults = await RestatePromise.all(
        tasks.map((task, i) =>
          ctx.run(`research-${i}`, async () => {
            const { text } = await generateText({
              model,
              system:
                "You are a research assistant. Provide a concise, factual answer.",
              prompt: task,
            });
            return { question: task, answer: text };
          }),
        ),
      );

      // Step 3: Combine results into a report
      const { text: report } = await generateText({
        model,
        system:
          "You are a report writer. Combine the research findings into a cohesive report.",
        prompt: `Topic: ${req.topic}\n\nResearch findings:\n${JSON.stringify(workerResults, null, 2)}`,
      });

      return { report, taskCount: tasks.length };
    },
  },
});
// <end_here>

restate.serve({ services: [agent] });
