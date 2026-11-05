// 10: Expose a whole Restate service to the agent as one tool, from its `iface` contract.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent, serviceTool} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

// The interface (contract). Its descriptions are surfaced to the model by serviceTool,
// so the agent knows what each handler does without any extra wiring.
export const refundIface = restate.iface.service("RefundService", {
  getPolicy: restate.iface.schemas({
    input: z.object({}),
    output: z.object({refundWindowDays: z.number(), requiresReceipt: z.boolean()}),
    description: "Read the refund policy.",
  }),
  issueRefund: restate.iface.schemas({
    input: z.object({orderId: z.string(), amountCents: z.number().int().positive()}),
    output: z.object({refundId: z.string(), status: z.string()}),
    description: "Issue a refund for an order. Amount is in cents.",
  }),
});

// The implementation: an ordinary Restate service, registered in services.ts.
export const refundService = restate.implement(refundIface, {
  handlers: {
    *getPolicy() {
      return {refundWindowDays: 30, requiresReceipt: true};
    },
    *issueRefund({orderId}) {
      return {refundId: `re_${orderId}`, status: "issued"};
    },
  },
});

// One tool exposes every handler of the service; the model selects which to invoke.
const support = agent({
  model,
  instructions:
    "Help the user with refunds. Use the refund tool to read the policy and to issue refunds.",
  maxSteps: 6,
  tools: {
    refund: serviceTool(refundIface),
  },
});

export const refundAgent = restate.service({
  name: "RefundAgent",
  handlers: {
    ask: restate.schemas(
      {
        input: z.object({
          message: z.string().default("Refund order O-99 for $12.50 and tell me the refund policy."),
        }),
        output: z.string(),
      },
      function* ({message}) {
        const result = yield* support.run(message);
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
  },
});
