import * as restate from "@restatedev/restate-sdk";
import bookingWithRollbackAgent from "./rollback-agent";
import mcpAgent from "./mcp-agent";

restate.serve({
  services: [bookingWithRollbackAgent, mcpAgent],
});
