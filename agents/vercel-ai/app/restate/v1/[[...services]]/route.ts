import * as restate from "@restatedev/restate-sdk/fetch";

import multi_tool from "@/restate/services/multi_tool";
import chat from "@/restate/services/chat";
import human from "@/restate/services/human_approval";
import remote from "@/restate/services/remote_llm";
import { multiAgentLoanWorkflow, riskAssementAgent } from "@/restate/services/multi_agent";
import { models } from "@/restate/ai_infra";
import { pubsub } from "@/restate/services/pubsub";

const services = restate
  .endpoint()
  .bind(chat)
  .bind(human)
  .bind(multi_tool)
  .bind(pubsub)
  .bind(multiAgentLoanWorkflow)
  .bind(riskAssementAgent)
  .bind(remote)
  .bind(models)
  .handler();

export function GET(request: Request) {
  return services.fetch(request);
}

export function POST(request: Request) {
  return services.fetch(request);
}
