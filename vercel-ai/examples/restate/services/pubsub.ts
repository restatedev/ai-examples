import * as restate from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";
import { z } from "zod";

const PULL_TIMEOUT = parseInt(process.env.PULL_TIMEOUT ?? "30000"); // 30 seconds

interface Subscription {
  offset: number;
  id: string;
}

interface Notification {
  newOffset: number;
  newMessages: any[];
}

interface PubSubState {
  messages: any[];
  subscription: Subscription[];
}

const handler = restate.handlers.object;

export const pubsub = restate.object({
  name: "pubsub",
  handlers: {
    pull: handler.shared(
      {
        input: serde.zod(
          z.object({
            offset: z.number(),
          })
        ),
        output: serde.zod(
          z.object({
            messages: z.any().array(),
            nextOffset: z.number(),
          })
        ),
      },
      async (ctx: restate.ObjectSharedContext<PubSubState>, { offset }) => {
        const messages = (await ctx.get("messages")) ?? [];
        if (offset < messages.length) {
          return {
            messages: messages.slice(offset),
            nextOffset: messages.length,
          };
        }
        const { id, promise } = ctx.awakeable<Notification>();
        ctx.objectSendClient(pubsub, ctx.key).subscribe({ offset, id });
        const { newMessages, newOffset } = await promise.orTimeout(
          PULL_TIMEOUT
        );
        return {
          messages: newMessages,
          nextOffset: newOffset,
        };
      }
    ),

    publish: async (
      ctx: restate.ObjectContext<PubSubState>,
      message: unknown
    ) => {
      const messages = (await ctx.get("messages")) ?? [];
      messages.push(message);
      ctx.set("messages", messages);

      const subscriptions = (await ctx.get("subscription")) ?? [];
      for (const { id, offset } of subscriptions) {
        const notification = {
          newOffset: messages.length,
          newMessages: messages.slice(offset),
        };
        ctx.resolveAwakeable(id, notification);
      }
      ctx.clear("subscription");
    },

    subscribe: async (
      ctx: restate.ObjectContext<PubSubState>,
      subscription: Subscription
    ) => {
      const messages = (await ctx.get("messages")) ?? [];
      if (subscription.offset < messages.length) {
        const notification = {
          newOffset: messages.length,
          newMessages: messages.slice(subscription.offset),
        };
        ctx.resolveAwakeable(subscription.id, notification);
        return;
      }
      const sub = (await ctx.get("subscription")) ?? [];
      sub.push(subscription);
      ctx.set("subscription", sub);
    },
  },
});

export const publishMessage = <T>(
  ctx: restate.Context,
  topic: string,
  message: T
) => {
  ctx.objectSendClient(pubsub, topic).publish(message);
};

export type PubSub = typeof pubsub;
