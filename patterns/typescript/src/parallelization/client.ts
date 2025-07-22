import * as restate from "@restatedev/restate-sdk-clients";
import { parallelizationService } from "./app";

// Define the service for client usage
const ParallelizationService: typeof parallelizationService = {
  name: "ParallelizationService",
};

const stakeholders = [
  `Customers:
  - Price sensitive
  - Want better tech
  - Environmental concerns`,
  `Employees:
  - Job security worries
  - Need new skills
  - Want clear direction`,
  `Investors:
  - Expect growth
  - Want cost control
  - Risk concerns`,
  `Suppliers:
  - Capacity constraints
  - Price pressures
  - Tech transitions`,
];

interface ParallelizationRequest {
  prompt: string;
  inputs: string[];
}

async function main() {
  const rs = restate.connect({ url: "http://localhost:8080" });

  const data: ParallelizationRequest = {
    prompt: `Analyze how market changes will impact this stakeholder group.
    Provide specific impacts and recommended actions.
    Format with clear sections and priorities.`,
    inputs: stakeholders,
  };

  try {
    const response = await rs
      .serviceClient(ParallelizationService)
      .run_in_parallel(data);

    response.forEach((item) => console.log(item));
  } catch (error) {
    console.error("Error:", error);
  }
}

main();
