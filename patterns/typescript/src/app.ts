import * as restate from "@restatedev/restate-sdk";
import { evaluatorOptimizer } from "./evaluator_optimizer/app";
import { callChainingService } from "./chaining/app";
import { parallelizationService } from "./parallelization/app";
import { routingService } from "./routing/app";
import { flexibleOrchestrator } from "./orchestrator_workers/app";
import { humanInTheLoopService } from "./human_in_the_loop/app";

restate
  .endpoint()
  .bind(callChainingService)
  .bind(evaluatorOptimizer)
  .bind(parallelizationService)
  .bind(routingService)
  .bind(flexibleOrchestrator)
  .bind(humanInTheLoopService)
  .listen(9080);
