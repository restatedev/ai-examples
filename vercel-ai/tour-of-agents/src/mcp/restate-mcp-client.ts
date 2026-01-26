import * as restate from "@restatedev/restate-sdk";
import { createMCPClient, MCPClient, MCPClientConfig } from "@ai-sdk/mcp";
import { AISDKError, Schema, ToolExecutionOptions } from "ai";
import { RunOptions, TerminalError } from "@restatedev/restate-sdk";
// Extract all types from the MCPClient interface since they're not exported
type ToolSchemas =
  | Record<
      string,
      {
        inputSchema: any;
      }
    >
  | "automatic"
  | undefined;
type ToolsResult = Awaited<ReturnType<MCPClient["tools"]>>;
type PaginatedRequest = Parameters<MCPClient["listResources"]>[0] extends {
  params?: infer P;
}
  ? { params: P }
  : never;
type RequestOptions = Parameters<MCPClient["listResources"]>[0] extends {
  options?: infer O;
}
  ? O
  : never;
type ListResourcesResult = Awaited<ReturnType<MCPClient["listResources"]>>;
type ReadResourceResult = Awaited<ReturnType<MCPClient["readResource"]>>;
type ListResourceTemplatesResult = Awaited<
  ReturnType<MCPClient["listResourceTemplates"]>
>;
type ListPromptsResult = Awaited<
  ReturnType<MCPClient["experimental_listPrompts"]>
>;
type GetPromptResult = Awaited<ReturnType<MCPClient["experimental_getPrompt"]>>;

export interface ListToolResult {
  description?: string;
  inputSchema?: Schema<unknown>;
}

export async function createRestateMCPClient(
  ctx: restate.Context,
  config: MCPClientConfig,
  runOptions?: RunOptions<any>,
) {
  // check if transport is regular HTTP
  if (!("type" in config.transport) || config.transport.type !== "http") {
    throw new TerminalError(
      "RestateMCPClient only supports HTTP transport. No SSE or stdin/out transports are supported.",
    );
  }
  const retryPolicy = runOptions || {
    initialRetryInterval: { milliseconds: 1000 },
    maxRetryAttempts: 10,
  };

  const client = await createMCPClient(config);
  return new RestateMCPClient(
    ctx,
    config.name ?? "RestateMCPClient",
    client,
    retryPolicy,
  );
}

/**
 * MCP Client that wraps all server calls in Restate's ctx.run for durability and observability.
 *
 * This wrapper ensures that all MCP server interactions are properly tracked and can be
 * replayed in case of failures when using Restate workflows.
 */
export class RestateMCPClient {
  private readonly client: MCPClient;
  private readonly ctx: restate.Context;
  private readonly name: string;
  private readonly retryPolicy: RunOptions<any>;

  constructor(
    ctx: restate.Context,
    name: string,
    client: MCPClient,
    retryPolicy: RunOptions<any>,
  ) {
    this.client = client;
    this.name = name;
    this.ctx = ctx;
    this.retryPolicy = retryPolicy;
  }

  /**
   * Get tools from the MCP server, wrapped in ctx.run for durability
   */
  async tools<TOOL_SCHEMAS extends ToolSchemas = "automatic">(options?: {
    schemas?: TOOL_SCHEMAS;
  }) {
    const tools = (await this.ctx.run(
      `${this.name}-mcp-list-tools`,
      async () => await this.client.tools(options),
    )) as Record<string, ListToolResult>;

    return Object.fromEntries(
      Object.entries(tools).map(([toolName, toolResult]) => [
        toolName,
        {
          description: toolResult.description,
          execute: async (input: unknown, options: ToolExecutionOptions) => {
            return this.ctx.run(
              `${toolName}-mcp-tool-execute`,
              async () => {
                // Retrieve tools again to get access to the execute function
                const toolDefs = await this.client.tools();
                const tool = toolDefs[toolName];
                if (!tool) {
                  throw new TerminalError(`Tool ${toolName} not found`);
                }
                try {
                  return await tool.execute(input, options);
                } catch (error) {
                  if (isMCPClientError(error)) {
                    throw new TerminalError(
                      `${error.name} - ${error.message}`,
                      {
                        cause: error.cause,
                      },
                    );
                  }
                  throw error;
                }
              },
              this.retryPolicy,
            );
          },
          inputSchema: {
            ...toolResult.inputSchema,
            _type: undefined,
            validate: undefined,
            [Symbol.for("vercel.ai.schema")]: true,
            [Symbol.for("vercel.ai.validator")]: true,
          },
          type: "dynamic",
        },
      ]),
    ) as ToolsResult;
  }

  /**
   * List resources from the MCP server, wrapped in ctx.run for durability
   */
  async listResources(options?: {
    params?: PaginatedRequest["params"];
    options?: RequestOptions;
  }): Promise<ListResourcesResult> {
    return this.ctx.run(
      `${this.name}-mcp-list-resources`,
      async () => {
        try {
          return await this.client.listResources(options);
        } catch (error) {
          if (isMCPClientError(error)) {
            // For example client closed, unparsable response, etc.
            throw new TerminalError(`${error.name} - ${error.message}`, {
              cause: error.cause,
            });
          }
          throw error;
        }
      },
      this.retryPolicy,
    );
  }

  /**
   * Read a specific resource from the MCP server, wrapped in ctx.run for durability
   */
  async readResource(args: {
    uri: string;
    options?: RequestOptions;
  }): Promise<ReadResourceResult> {
    return this.ctx.run(
      `${this.name}-mcp-read-resource-${args.uri}`,
      async () => {
        try {
          return await this.client.readResource(args);
        } catch (error) {
          if (isMCPClientError(error)) {
            // For example client closed, unparsable response, etc.
            throw new TerminalError(`${error.name} - ${error.message}`, {
              cause: error.cause,
            });
          }
          throw error;
        }
      },
      this.retryPolicy,
    );
  }

  /**
   * List resource templates from the MCP server, wrapped in ctx.run for durability
   */
  async listResourceTemplates(options?: {
    options?: RequestOptions;
  }): Promise<ListResourceTemplatesResult> {
    return this.ctx.run(
      `${this.name}-mcp-list-resource-templates`,
      async () => {
        try {
          return await this.client.listResourceTemplates(options);
        } catch (error) {
          if (isMCPClientError(error)) {
            // For example client closed, unparsable response, etc.
            throw new TerminalError(`${error.name} - ${error.message}`, {
              cause: error.cause,
            });
          }
          throw error;
        }
      },
      this.retryPolicy,
    );
  }

  /**
   * List prompts from the MCP server, wrapped in ctx.run for durability
   */
  async experimental_listPrompts(options?: {
    params?: PaginatedRequest["params"];
    options?: RequestOptions;
  }): Promise<ListPromptsResult> {
    return this.ctx.run(
      `${this.name}-mcp-list-prompts`,
      async () => {
        try {
          return await this.client.experimental_listPrompts(options);
        } catch (error) {
          if (isMCPClientError(error)) {
            // For example client closed, unparsable response, etc.
            throw new TerminalError(`${error.name} - ${error.message}`, {
              cause: error.cause,
            });
          }
          throw error;
        }
      },
      this.retryPolicy,
    );
  }

  /**
   * Get a specific prompt from the MCP server, wrapped in ctx.run for durability
   */
  async experimental_getPrompt(args: {
    name: string;
    arguments?: Record<string, unknown>;
    options?: RequestOptions;
  }): Promise<GetPromptResult> {
    return this.ctx.run(
      `${this.name}-mcp-get-prompt-${args.name}`,
      async () => {
        try {
          return await this.client.experimental_getPrompt(args);
        } catch (error) {
          if (isMCPClientError(error)) {
            // For example client closed, unparsable response, etc.
            throw new TerminalError(`${error.name} - ${error.message}`, {
              cause: error.cause,
            });
          }
          throw error;
        }
      },
      this.retryPolicy,
    );
  }

  /**
   * Close the MCP client connection, wrapped in ctx.run for durability
   */
  async close(): Promise<void> {
    await this.client.close();
  }
}

function isMCPClientError(error: unknown): error is AISDKError {
  return AISDKError.isInstance(error) && error.name == "MCPClientError";
}
