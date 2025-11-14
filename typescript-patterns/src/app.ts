import * as restate from "@restatedev/restate-sdk";
import chainingService from "./chaining";
import chat from "./chat";
import evaluatorOptimizer from "./evaluator-optimizer";
import humanInTheLoop from "./human-in-the-loop";
import parallelTools from "./parallel-tools";
import parallelAgents from "./parallel-agents";
import routingToAgent from "./routing-to-agent";
import routingToRemoteAgent from "./routing-to-remote-agent";
import routingToTools from "./routing-to-tools";
import {
  crmService,
  accountAgent,
  billingAgent,
  productAgent,
} from "./utils/utils";

restate.serve({
  services: [
    chainingService,
    chat,
    evaluatorOptimizer,
    humanInTheLoop,
    parallelTools,
    parallelAgents,
    routingToAgent,
    routingToRemoteAgent,
    routingToTools,
    crmService,
    accountAgent,
    billingAgent,
    productAgent,
  ],
  port: 9080,
});
