/**
 * LLM Prompt Chaining
 *
 * Build fault-tolerant processing pipelines where each step transforms the previous step's output.
 * If any step fails, Restate automatically resumes from that point.
 *
 * Input → Analysis → Extraction → Summary → Result
 */
import * as restate from "@restatedev/restate-sdk";
import { Context } from "@restatedev/restate-sdk";
import llmCall from "./utils/llm";
import { zodPrompt } from "./utils/utils";
import { openai } from "@ai-sdk/openai";

const examplePrompt = `Q3 Performance Summary:
    Our customer satisfaction score rose to 92 points this quarter.
    Revenue grew by 45% compared to last year.
    Market share is now at 23% in our primary market.
    Customer churn decreased to 5% from 8%.`;

// <start_here>
async function process(ctx: Context, report: { message: string }) {
  // Step 1: Extract metrics
  const extract = await ctx.run(
    "Extract metrics",
    async () =>
      llmCall(`Extract numerical values and their metrics from the text. 
            Format as 'Metric: Value' per line. Input: ${report.message}`),
    { maxRetryAttempts: 3 },
  );

  // Step 2: Process the result from Step 1
  const sortedMetrics = await ctx.run(
    "Sort metrics",
    async () =>
      llmCall(
        `Sort lines in descending order by value. Input: ${extract.text}`,
      ),
    { maxRetryAttempts: 3 },
  );

  // Step 3: Format as table
  const table = await ctx.run(
    "Format as table",
    async () =>
      llmCall(
        `Format the data as a markdown table with columns 
         'Metric Name' and 'Value'. Input: ${sortedMetrics.text}`,
      ),
    { maxRetryAttempts: 3 },
  );

  return table.text;
}
// <end_here>

export default restate.service({
  name: "CallChainingService",
  handlers: {
      process: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      process,
    ),
  },
});
