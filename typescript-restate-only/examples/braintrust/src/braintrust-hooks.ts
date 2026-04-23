/**
 * Restate hooks that send traces to Braintrust.
 *
 * Creates Braintrust spans for each Restate handler invocation and ctx.run()
 * call. Because Braintrust's traced() propagates context via AsyncLocalStorage,
 * any wrapAISDK-instrumented call automatically nests under the Restate spans.
 *
 * Setup:
 *   Set BRAINTRUST_API_KEY and BRAINTRUST_PROJECT_ID env vars, then:
 *
 *   import { braintrustTracingHook } from "./braintrust-hooks.js";
 *
 *   restate.serve({
 *     services: [myService],
 *     defaultServiceOptions: { hooks: [braintrustTracingHook] },
 *   });
 */

import { initLogger } from "braintrust";
import { propagation } from "@opentelemetry/api";
import {
  W3CTraceContextPropagator,
  W3CBaggagePropagator,
  CompositePropagator,
} from "@opentelemetry/core";
import { parentFromHeaders, setupOtelCompat } from "@braintrust/otel";
import type { HooksProvider } from "@restatedev/restate-sdk";

setupOtelCompat();

// Register W3C propagators so parentFromHeaders can parse traceparent + baggage
propagation.setGlobalPropagator(
  new CompositePropagator({
    propagators: [new W3CTraceContextPropagator(), new W3CBaggagePropagator()],
  }),
);

const logger = initLogger({
  projectId: process.env.BRAINTRUST_PROJECT_ID,
  apiKey: process.env.BRAINTRUST_API_KEY,
});

export const braintrustTracingHook: HooksProvider = (ctx) => {
  const { service, handler, key } = ctx.request.target;
  const target = key ? `${service}/${key}/${handler}` : `${service}/${handler}`;

  // Bridge Restate's W3C traceparent to a Braintrust parent string.
  // parentFromHeaders needs both traceparent and a baggage header with
  // the Braintrust project info to construct a valid parent.
  const rawTp = ctx.request.attemptHeaders.get("traceparent");
  const traceparent = Array.isArray(rawTp) ? rawTp[0] : rawTp;
  const braintrustParent = traceparent
    ? parentFromHeaders({
        traceparent,
        baggage: `braintrust.parent=project_id:${process.env.BRAINTRUST_PROJECT_ID}`,
      })
    : undefined;

  return {
    interceptor: {
      handler: async (next) => {
        let suspended: unknown;
        await logger.traced(
          async (span) => {
            try {
              await next();
            } catch (e) {
              if (isSuspendedError(e)) {
                span.log({ metadata: { status: "suspended" } });
                suspended = e;
              } else {
                throw e;
              }
            }
          },
          { name: target, parent: braintrustParent },
        );
        if (suspended) throw suspended;
      },

      run: (name, next) => logger.traced(next, { name: `run (${name})` }),
    },
  };
};

// Suspension uses error code 599 in the Restate SDK
function isSuspendedError(e: unknown): boolean {
  return e instanceof Error && "code" in e && e.code === 599;
}