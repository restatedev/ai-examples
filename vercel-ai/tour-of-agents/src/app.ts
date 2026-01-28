import * as restate from "@restatedev/restate-sdk";
import weatherAgent from "./durableexecution/agent";
import humanClaimApprovalAgent from "./humanintheloop/agent";
import humanClaimApprovalWithTimeoutsAgent from "./humanintheloop/agent-with-timeout";
import chatAgent from "./chat/agent";
import {
  subWorkflowClaimApprovalAgent,
  humanApprovalWorfklow,
} from "./orchestration/sub-workflow-agent";
import multiAgentClaimApproval from "./orchestration/multi-agent";
import parallelAgentClaimApproval from "./parallelwork/parallel-agents";
import parallelToolClaimAgent from "./parallelwork/parallel-tools-agent";
import stopOnTerminalErrorAgent from "./errorhandling/stop-on-terminal-tool-agent";
import failOnTerminalErrorAgent from "./errorhandling/fail-on-terminal-tool-agent";
import {
  eligibilityAgent,
  fraudCheckAgent,
  rateComparisonAgent,
} from "./utils";

restate.serve({
  services: [
    // Durable execution examples
    weatherAgent,
    // Human-in-the-loop examples
    humanClaimApprovalAgent,
    humanClaimApprovalWithTimeoutsAgent,
    // Chat example
    chatAgent,
    // Orchestration examples
    subWorkflowClaimApprovalAgent,
    humanApprovalWorfklow,
    multiAgentClaimApproval,
    // Parallel execution examples
    parallelToolClaimAgent,
    parallelAgentClaimApproval,
    // Error handling examples
    stopOnTerminalErrorAgent,
    failOnTerminalErrorAgent,
    // Utils and sub-agents
    eligibilityAgent,
    fraudCheckAgent,
    rateComparisonAgent,
  ],
});
