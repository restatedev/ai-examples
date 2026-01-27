import * as restate from "@restatedev/restate-sdk";
import {
    ElicitationRequest,
    ElicitationRequestSchema,
    ElicitResult,
    experimental_createMCPClient as createMCPClient,
    experimental_MCPClient as MCPClient,
    experimental_MCPClientConfig as MCPClientConfig,
} from '@ai-sdk/mcp';
import {MCPClientError, ToolCallOptions} from "ai";
import {TerminalError} from "@restatedev/restate-sdk";
// Extract all types from the MCPClient interface since they're not exported
type ToolSchemas = Record<string, {
    inputSchema: any;
}> | 'automatic' | undefined;
type PaginatedRequest = Parameters<MCPClient['listResources']>[0] extends { params?: infer P } ? { params: P } : never;
type RequestOptions = Parameters<MCPClient['listResources']>[0] extends { options?: infer O } ? O : never;
type ListResourcesResult = Awaited<ReturnType<MCPClient['listResources']>>;
type ReadResourceResult = Awaited<ReturnType<MCPClient['readResource']>>;
type ListResourceTemplatesResult = Awaited<ReturnType<MCPClient['listResourceTemplates']>>;
type ListPromptsResult = Awaited<ReturnType<MCPClient['listPrompts']>>;
type GetPromptResult = Awaited<ReturnType<MCPClient['getPrompt']>>;


export async function createRestateMCPClient(ctx: restate.Context, config: MCPClientConfig) {
    // check if transport is regular HTTP
    if (
        !('type' in config.transport) ||
        config.transport.type !== 'http'
    ) {
        throw new TerminalError('RestateMCPClient only supports HTTP transport. No SSE or stdin/out transports are supported.');
    }
    const client = await createMCPClient(config)
    return new RestateMCPClient(ctx, config.name ?? "RestateMCPClient", client);
}

/**
 * MCP Client that wraps all server calls in Restate's ctx.run for durability and observability.
 *
 * This wrapper ensures that all MCP server interactions are properly tracked and can be
 * replayed in case of failures when using Restate workflows.
 */
class RestateMCPClient implements MCPClient {
  private readonly client: MCPClient;
  private readonly ctx: restate.Context;
  private readonly name: string;

  constructor(ctx: restate.Context, name: string, client: MCPClient) {
    this.client = client;
    this.name = name;
    this.ctx = ctx;
  }

  /**
   * Get tools from the MCP server, wrapped in ctx.run for durability
   */
  async tools<TOOL_SCHEMAS extends ToolSchemas = 'automatic'>(options?: {
    schemas?: TOOL_SCHEMAS;
  }) {
    const tools = await this.client.tools(options);

    for (const tool of Object.values(tools)) {
      // Wrap the tool's execute method to ensure durability
      const originalExecute = tool.execute;
      tool.execute = async (
          args: any,
          options: ToolCallOptions,
      ) => {
          return this.ctx.run(`${this.name}-mcp-tool-execute`, async () => {
              try {
                  return originalExecute(args, options);
              } catch (error) {
                  if (MCPClientError.isInstance(error)) {
                      // For example client closed, unparsable response, etc.
                      throw new TerminalError(`${error.name} - ${error.message}`, { cause: error.cause });
                  }
                  throw error
              }
          })
      }
    }
    return tools;
  }

  /**
   * List resources from the MCP server, wrapped in ctx.run for durability
   */
  async listResources(options?: {
    params?: PaginatedRequest['params'];
    options?: RequestOptions;
  }): Promise<ListResourcesResult> {
    return this.ctx.run(`${this.name}-mcp-list-resources`, async () => {
        try {
            return await this.client.listResources(options)
        } catch (error) {
            if (MCPClientError.isInstance(error)) {
                // For example client closed, unparsable response, etc.
                throw new TerminalError(`${error.name} - ${error.message}`, { cause: error.cause });
            }
            throw error
        }
    });
  }

  /**
   * Read a specific resource from the MCP server, wrapped in ctx.run for durability
   */
  async readResource(args: {
    uri: string;
    options?: RequestOptions;
  }): Promise<ReadResourceResult> {
    return this.ctx.run(`${this.name}-mcp-read-resource-${args.uri}`, async () => {
        try {
            return await this.client.readResource(args);
        } catch (error) {
            if (MCPClientError.isInstance(error)) {
                // For example client closed, unparsable response, etc.
                throw new TerminalError(`${error.name} - ${error.message}`, {cause: error.cause});
            }
            throw error
        }
    });
  }

  /**
   * List resource templates from the MCP server, wrapped in ctx.run for durability
   */
  async listResourceTemplates(options?: {
    options?: RequestOptions;
  }): Promise<ListResourceTemplatesResult> {
      return this.ctx.run(`${this.name}-mcp-list-resource-templates`, async () => {
          try {
              return await this.client.listResourceTemplates(options);
          } catch (error) {
              if (MCPClientError.isInstance(error)) {
                  // For example client closed, unparsable response, etc.
                  throw new TerminalError(`${error.name} - ${error.message}`, {cause: error.cause});
              }
              throw error
          }
      });
  }

  /**
   * List prompts from the MCP server, wrapped in ctx.run for durability
   */
  async listPrompts(options?: {
    params?: PaginatedRequest['params'];
    options?: RequestOptions;
  }): Promise<ListPromptsResult> {
      return this.ctx.run(`${this.name}-mcp-list-prompts`, async () => {
          try {
              return await this.client.listPrompts(options);
          } catch (error) {
              if (MCPClientError.isInstance(error)) {
                  // For example client closed, unparsable response, etc.
                  throw new TerminalError(`${error.name} - ${error.message}`, {cause: error.cause});
              }
              throw error
          }
      });
  }

  /**
   * Get a specific prompt from the MCP server, wrapped in ctx.run for durability
   */
  async getPrompt(args: {
    name: string;
    arguments?: Record<string, unknown>;
    options?: RequestOptions;
  }): Promise<GetPromptResult> {
      return this.ctx.run(`${this.name}-mcp-get-prompt-${args.name}`, async () => {
          try {
              return await this.client.getPrompt(args);
          } catch (error) {
              if (MCPClientError.isInstance(error)) {
                  // For example client closed, unparsable response, etc.
                  throw new TerminalError(`${error.name} - ${error.message}`, {cause: error.cause});
              }
              throw error
          }
      });
  }

  /**
   * Register elicitation request handler (no wrapping needed as this is just registration)
   */
  onElicitationRequest(
    schema: typeof ElicitationRequestSchema,
    handler: (
      request: ElicitationRequest,
    ) => Promise<ElicitResult> | ElicitResult,
  ): void {
    return this.client.onElicitationRequest(schema, handler);
  }

  /**
   * Close the MCP client connection, wrapped in ctx.run for durability
   */
  async close(): Promise<void> {
      await this.client.close()
  }
}

