import * as restate from "@restatedev/restate-sdk";
import chainingService from "./chaining";

restate.serve({
  services: [chainingService],
  port: 9080,
});
