import { createPubsubClient } from "@restatedev/pubsub-client";
import { NextRequest } from "next/server";

const pubsub = createPubsubClient({
  url: process.env.INGRESS_URL || "http://localhost:8080",
  name: "pubsub",
});

export async function GET(request: NextRequest, { params }: any) {
  const topic = (await params).topic;
  const offset = Number(request.nextUrl.searchParams.get("offset") || 0);

  const stream = pubsub.sse({
    topic,
    offset,
    signal: request.signal,
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
    },
  });
}
