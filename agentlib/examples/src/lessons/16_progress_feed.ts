// 16: Publish an agent's progress to subscribers while it works.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent, tool, type ProgressEvent} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

/** A tiny pub/sub object: each subscriber receives the next published event. */
export const progressFeed = restate.object({
  name: "ProgressFeed",
  handlers: {
    *publish(event: ProgressEvent) {
      const subscribers = (yield* restate.state().get<string[]>("subscribers")) ?? [];
      for (const id of subscribers) restate.resolveAwakeable(id, event);
      restate.state().clear("subscribers");
    },
    *addSubscriber(id: string) {
      const subscribers = (yield* restate.state().get<string[]>("subscribers")) ?? [];
      restate.state().set("subscribers", [...subscribers, id]);
    },
    *subscribe() {
      const {id, promise} = restate.awakeable<ProgressEvent>();
      restate.sendClient(progressFeed, restate.handlerRequest().key!).addSubscriber(id);
      return yield* promise;
    },
  },
  // Shared: subscribers wait without blocking publish.
  options: {handlers: {subscribe: {shared: true}}},
});

const auditor = agent({
  model,
  instructions: "Audit stock. Use countStock, then name the warehouse with the least stock.",
  tools: {
    countStock: tool({
      description: "Count stock in demo warehouses.",
      input: z.object({warehouses: z.array(z.string()).max(10)}),
      *execute({warehouses}, context) {
        const counts: Record<string, number> = {};
        for (const warehouse of warehouses) {
          counts[warehouse] = warehouse.length * 7; // demo count
          yield* context.progress(`counted ${warehouse}`);
        }
        return counts;
      },
    }),
  },
});

export const inventoryAudit = restate.service({
  name: "InventoryAudit",
  handlers: {
    audit: restate.schemas(
      {
        input: z.object({
          job: z.string().default("audit-1"),
          request: z.string().default("Count stock in Berlin, Lisbon, and Oslo."),
        }),
        output: z.string(),
      },
      function* ({job, request}) {
        const feed = restate.sendClient(progressFeed, job);
        const result = yield* auditor.run(request, {
          // A one-way send, so the agent does not wait for subscribers.
          *onProgress(event) {
            feed.publish(event);
          },
        });
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
  },
});
