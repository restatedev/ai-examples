// Every lesson's services, in tutorial order.
import {hello} from "./01_hello.js";
import {ticketLookup} from "./02_tools.js";
import {chatSession} from "./03_conversation.js";
import {ticketTriage} from "./04_structured_output.js";
import {codeReview} from "./05_evaluator_optimizer.js";
import {ticketApproval} from "./06_human_approval.js";
import {racingAgents} from "./07_racing_agents.js";
import {researchReport, researchWorker} from "./08_research_report.js";
import {aiSession} from "./09_support_session.js";
import {refundAgent, refundService} from "./10_service_tool.js";
import {codingAgent} from "./11_coding_agent.js";
import {supportRouter} from "./12_routing.js";
import {guardedBooking} from "./13_tool_guardrail.js";
import {webResearch} from "./14_web_search.js";
import {peerAuthor, peerReview, peerReviewer} from "./15_peer_review_rpc.js";
import {inventoryAudit, progressFeed} from "./16_progress_feed.js";
import {docsGuide} from "./17_mcp_tools.js";

export const services = [
  hello,
  ticketLookup,
  chatSession,
  ticketTriage,
  codeReview,
  ticketApproval,
  racingAgents,
  researchReport,
  researchWorker,
  aiSession,
  refundService,
  refundAgent,
  codingAgent,
  supportRouter,
  guardedBooking,
  webResearch,
  peerAuthor,
  peerReviewer,
  peerReview,
  progressFeed,
  inventoryAudit,
  docsGuide,
];
