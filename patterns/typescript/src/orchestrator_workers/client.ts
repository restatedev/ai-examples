import * as restate from "@restatedev/restate-sdk-clients";
import flexibleOrchestrator, { OrchestrationRequest } from "./app";

// Define the service for client usage
const FlexibleOrchestrator: typeof flexibleOrchestrator = {
  name: "FlexibleOrchestrator",
};

const ORCHESTRATOR_PROMPT = `
Analyze this task and break it down into 2-3 distinct approaches:

Task: {task}

Return your response in this format:

<analysis>
Explain your understanding of the task and which variations would be valuable.
Focus on how each approach serves different aspects of the task.
</analysis>

<tasks>
    <task>
    <type>formal</type>
    <description>Write a precise, technical version that emphasizes specifications</description>
    </task>
    <task>
    <type>conversational</type>
    <description>Write an engaging, friendly version that connects with readers</description>
    </task>
</tasks>
`;

const WORKER_PROMPT = `
Generate content based on:
Task: {original_task}
Style: {task_type}
Guidelines: {task_description}

Return your response in this format:

<response>
Your content here, maintaining the specified style and fully addressing requirements.
</response>
`;

async function main() {
  const rs = restate.connect({ url: "http://localhost:8080" });

  const data: OrchestrationRequest = {
    orchestratorPrompt: ORCHESTRATOR_PROMPT,
    workerPrompt: WORKER_PROMPT,
    task: "Write a product description for a new eco-friendly water bottle",
    llmContext: {
      target_audience: "environmentally conscious millenials",
      key_features: ["plastic-free", "insulated", "lifetime warranty"],
    },
  };

  try {
    const response = await rs.serviceClient(FlexibleOrchestrator).process(data);

    console.log(JSON.stringify(response, null, 2));
  } catch (error) {
    console.error("Error:", error);
  }
}

main();
