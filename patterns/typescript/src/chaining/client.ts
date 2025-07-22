import * as restate from "@restatedev/restate-sdk-clients";
import { callChainingService } from "./app";

export const CallChainingService: typeof callChainingService = {
  name: "CallChainingService",
};

const dataProcessingSteps = [
  `Extract only the numerical values and their associated metrics from the text.
   Format each as 'value: metric' on a new line.
   Example format:
   92: customer satisfaction
   45%: revenue growth`,
  `Convert all numerical values to percentages where possible.
   If not a percentage or points, convert to decimal (e.g., 92 points -> 92%).
   Keep one number per line.
   Example format:
   92%: customer satisfaction
   45%: revenue growth`,
  `Sort all lines in descending order by numerical value.
   Keep the format 'value: metric' on each line.
   Example:
   92%: customer satisfaction
   87%: employee satisfaction`,
  `Format the sorted data as a markdown table with columns:
   | Metric | Value |
   |:--|--:|
   | Customer Satisfaction | 92% |`,
];

const report = `
Q3 Performance Summary:
Our customer satisfaction score rose to 92 points this quarter.
Revenue grew by 45% compared to last year.
Market share is now at 23% in our primary market.
Customer churn decreased to 5% from 8%.
New user acquisition cost is $43 per user.
Product adoption rate increased to 78%.
Employee satisfaction is at 87 points.
Operating margin improved to 34%.
`;

async function main() {
  // Connect to Restate
  const rs = restate.connect({ url: "http://localhost:8080" });

  const request = {
    input: report,
    prompts: dataProcessingSteps,
  };

  try {
    // Request-response call
    const response = await rs
      .serviceClient(CallChainingService)
      .chain_call(request);
    console.log("Response:", response);
  } catch (error) {
    console.error("Error:", error);
  }
}

main();
