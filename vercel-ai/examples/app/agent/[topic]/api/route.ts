import { NextRequest } from "next/server";
import * as clients from "@restatedev/restate-sdk-clients";
import { Tool } from "@/restate/services/multi_tool";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ topic: string }> },
) {
  const { topic } = await params;
  const { message } = await request.json();
  const ingressUrl = process.env.INGRESS_URL || "http://localhost:8080";

  const ingress = clients.connect({
    url: ingressUrl,
  });

  await ingress
    .serviceSendClient<Tool>({ name: "tools" })
    .message({ prompt: message, topic });

  return Response.json({ ok: true });
}
