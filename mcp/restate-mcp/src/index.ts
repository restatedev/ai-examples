import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";


const ADMIN_URL = process.env.ADMIN_URL ?? "http://localhost:9070";
const INGRESS_BASE_URL = process.env.INGRESS_URL ?? "http://localhost:8080";

class AdminClient {
  constructor(private adminUrl: string) {}

  async deployments() {
    const res = await fetch(`${this.adminUrl}/deployments`, {
      headers: {
        accept: "json",
      },
      body: null,
      method: "GET",
    });

    return await res.json();
  }

  async serviceNames(): Promise<string[]> {
    const res = await this.deployments();
    const names = new Set<string>();
    for (const deployment of res.deployments) {
      for (const service of deployment.services) {
        names.add(service.name);
      }
    }
    return [...names];
  }

  async serviceSpec(serviceName: string) {
    const res = await fetch(`${this.adminUrl}/services/${serviceName}`, {
      headers: {
        accept: "json",
      },
      body: null,
      method: "GET",
    });

    return res.json();
  }

  async handlersWithLabel(label: string): Promise<{ service : string ; name: string; description: string ; inputSchema: any ; }[]> {
    const handlers = [];
    for (const serviceName of await this.serviceNames()) {
      const spec = await this.serviceSpec(serviceName);
      for (const handler of spec.handlers ?? []) {
        if (handler.metadata && label in handler.metadata) {
          handlers.push({
            service: serviceName,
            name: handler.name,
            description: handler.documentation,
            inputSchema: handler.input_json_schema,
          });
        }
      }
    }
    return handlers;
  }
}

async function main() {
	let toolUrls = new Map<string, string>();

  const server = new Server(
    {
      name: "restate-mcp-server",
      version: "0.0.1",
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => {
    const adminClient = new AdminClient(ADMIN_URL);
    const handlers = await adminClient.handlersWithLabel("mcp.type");

    toolUrls.clear();

    const tools = handlers.map((handler) => {
      const toolName = `${handler.service}_${handler.name}`;
      toolUrls.set(toolName, `${handler.service}/${handler.name}`);
      return {
        name: toolName,
        description: handler.description,
        inputSchema: handler.inputSchema,
      };
    });

    return {
      tools
    };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const toolName = request.params.name;
    const url = toolUrls.get(toolName);
    if (!url) {
      throw new Error(`Unknown tool: ${toolName}`);
    }
    let body: string | undefined = undefined;
    let headers: Record<string, string> = {};
    if (request.params.arguments) {
      body = JSON.stringify(request.params.arguments);
      headers["Content-Type"] = "application/json";
    }
    const res = await fetch(`${INGRESS_BASE_URL}/${url}`, {
      headers,
      body,
      method: "POST",
    });
    return res.json();
  });
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

