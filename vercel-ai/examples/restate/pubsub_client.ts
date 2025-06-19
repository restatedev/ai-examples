import * as clients from "@restatedev/restate-sdk-clients";
import type { PubSub } from "./services/pubsub";

export type PullOptions = {
  ingressUrl: string;
  topic: string;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  offset?: number;
  pullInterval?: number;
};

export function sse(opts: PullOptions): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    async start(controller) {
      try {
        controller.enqueue(encoder.encode(`event: ping\n`));
        const content = pullMessages(opts);
        for await (const message of content) {
          const chunk = `data: ${JSON.stringify(message)}\n\n`;
          controller.enqueue(encoder.encode(chunk));
        }
        controller.close();
      } catch (error) {
        controller.error(error);
        throw error;
      }
    },
  });
}

async function* pullMessages(opts: PullOptions) {
  const ingress = clients.connect({
    url: opts.ingressUrl,
    headers: opts.headers,
  });
  const signal = opts.signal;
  const delay = opts.pullInterval ?? 1000;
  let offset = opts.offset ?? 0;
  while (!(signal?.aborted ?? false)) {
    try {
      const { messages, nextOffset } = await ingress
        .objectClient<PubSub>({ name: "pubsub" }, opts.topic)
        .pull({ offset }, clients.rpc.opts({ signal }));
      for (const message of messages) {
        yield message;
      }
      offset = nextOffset;
    } catch (error) {
      if (!(error instanceof clients.HttpCallError) || error.status !== 408) {
        throw error;
      }
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
    if (opts.pullInterval) {
      await new Promise((resolve) => setTimeout(resolve, opts.pullInterval));
    }
  }
}
