import * as restate from "@restatedev/restate-sdk/fetch";

import multi_tool from "@/restate/services/multi_tool";
import chat from "@/restate/services/chat";
import human from "@/restate/services/human_approval";
import { multiAgentLoanWorkflow, riskAssementAgent } from "@/restate/services/multi_agent";
import { pubsub } from "@/restate/services/pubsub";
import { remote, translation } from "@/restate/services/remote_llm";

export const endpoint = restate.createEndpointHandler({
    services: [chat, human, multi_tool, pubsub, multiAgentLoanWorkflow,riskAssementAgent, translation, remote.models]
});