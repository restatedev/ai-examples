import * as restate from "@restatedev/restate-sdk-clients";
import evaluatorOptimizer, { LoopRequest } from "./app";

// Define the service for client usage
const EvaluatorOptimizer: typeof evaluatorOptimizer = {
  name: "EvaluatorOptimizer",
};

const evaluatorPrompt = `
Evaluate this following code implementation for:
1. code correctness
2. time complexity
3. style and best practices

You should be evaluating only and not attemping to solve the task.
Only output "PASS" if all criteria are met and you have no further suggestions for improvements.
Output your evaluation concisely in the following format.

<evaluation>PASS, NEEDS_IMPROVEMENT, or FAIL</evaluation>
<feedback>
What needs improvement and why.
</feedback>
`;

const generatorPrompt = `
Your goal is to complete the task based on <user input>. If there are feedback 
from your previous generations, you should reflect on them to improve your solution

Output your answer concisely in the following format: 

<thoughts>
[Your understanding of the task and feedback and how you plan to improve]
</thoughts>

<response>
[Your code implementation here]
</response>
`;

const task = `
<user input>
Implement a Stack with:
1. push(x)
2. pop()
3. getMin()
All operations should be O(1).
</user input>
`;

async function main() {
  // Connect to Restate
  const rs = restate.connect({ url: "http://localhost:8080" });

  const data: LoopRequest = {
    task,
    evaluatorPrompt,
    generatorPrompt,
  };

  try {
    const response = await rs.serviceClient(EvaluatorOptimizer).loop(data);

    console.log("\nResult:");
    console.log("-".repeat(40));
    console.log(response[0]);
    console.log("\nChain of thought:");
    console.log("-".repeat(40));
    console.log(JSON.stringify(response[1], null, 2));
  } catch (error) {
    console.error("Error:", error);
  }
}

main();
