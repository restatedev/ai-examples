// 06: Pause a tool for a human decision, then resume the same agent run.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent, asyncTool} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model, logApprovalCommand} from "../shared.js";

const support = agent({
  model,
  instructions:
    "Ticket approval lesson. Use closeTicket to close the requested demo ticket. If approval is denied, explain that the ticket was left unchanged and do not try again.",
  tools: {
    closeTicket: asyncTool({
      description: "Close a demo ticket after human approval. No external ticket is changed.",
      input: z.object({ticketId: z.string()}),
      needsApproval: true,
      async execute({ticketId}) {
        // Replace this demo result with an ordinary async API call.
        return {ticketId, status: "closed"};
      },
    }),
  },
});

export const ticketApproval = restate.object({
  name: "TicketApproval",
  handlers: {
    ask: restate.schemas(
      {
        input: z.object({message: z.string().default("Close ticket T-42 after I approve it.")}),
        output: z.string(),
      },
      function* ({message}) {
        const result = yield* support.run(message, {
          *onApproval(request) {
            // Replace this by requesting approval via email, or your preferred method
            logApprovalCommand("TicketApproval", request);
          },
        });
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
    approve: restate.schemas(
      {
        input: z.object({
          invocationId: z.string().describe("Use invocationId from the logged approval command."),
          signalName: z.string().describe("Use signalName from the logged approval command."),
          approved: z.boolean().default(false),
        }),
        output: z.boolean(),
      },
      function* ({invocationId, signalName, approved}) {
        restate.invocation(invocationId).signal(signalName).resolve(approved);
        return true;
      },
    ),
  },
  options: {
    // Approval can arrive while the exclusive ask handler is waiting.
    handlers: {approve: {shared: true}},
  },
});
