import * as restate from "@restatedev/restate-sdk/fetch";
import { agent } from "@/restate/services/agent";

const services = restate
  .endpoint()
  .bind(agent)
  .handler();

export function GET(request: Request) {
  return services.fetch(request);
}

export function POST(request: Request) {
  return services.fetch(request);
}
