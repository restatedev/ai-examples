import * as restate from "@restatedev/restate-sdk";
import { Context } from "@restatedev/restate-sdk";
import llmCall from "./utils/llm";
import { prompt } from "./utils/prompt";

const example_prompt = `Q3 Performance Summary:
    Our customer satisfaction score rose to 92 points this quarter.
    Revenue grew by 45% compared to last year.
    Market share is now at 23% in our primary market.
    Customer churn decreased to 5% from 8%.`;

/**
 * LLM Prompt Chaining
 *
 * Build fault-tolerant processing pipelines where each step transforms the previous step's output.
 * If any step fails, Restate automatically resumes from that exact point.
 *
 * Input → Analysis → Extraction → Summary → Result
 */
async function processReport(
  restate: Context,
  { message }: { message: string },
) {
  // Step 1: Process the initial input with the first prompt
  const result = await restate.run("Extract metrics", async () =>
    llmCall(`Extract only the numerical values and their associated metrics from the text. 
            Format each as 'metric name: metric' on a new line. Input: ${message}`),
  );

  // Step 2: Process the result from Step 1
  const result2 = await restate.run("Sort metrics", async () =>
    llmCall(
      `Sort all lines in descending order by numerical value. Input: ${result}`,
    ),
  );

  // Step 3: Process the result from Step 2
  return restate.run("Format as table", async () =>
    llmCall(
      `Format the sorted data as a markdown table with columns 'Metric Name' and 'Value'. Input: ${result2}`,
    ),
  );
}

export default restate.service({
  name: "CallChainingService",
  handlers: {
    run: restate.createServiceHandler(
      { input: prompt(example_prompt) },
      processReport,
    ),
  },
});
