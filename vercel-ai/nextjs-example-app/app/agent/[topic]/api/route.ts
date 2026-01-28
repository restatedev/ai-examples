import { NextRequest } from "next/server";
import * as clients from "@restatedev/restate-sdk-clients";
import { Agent } from "@/restate/services/agent";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ topic: string }> },
) {
  const { topic } = await params;
  const { message } = await request.json();
  const ingressUrl = process.env.INGRESS_URL || "http://localhost:8080";

  const ingress = clients.connect({ url: ingressUrl });

  await ingress
    .serviceSendClient<Agent>({ name: "agent" })
    .chat({ prompt: message, topic });

  return Response.json({ ok: true });
}
