import { openai } from "@ai-sdk/openai";
import { google } from "@ai-sdk/google";
import * as restate from "@restatedev/restate-sdk";
import {
  LanguageModelV1,
  LanguageModelV1CallOptions,
  LanguageModelV1Middleware,
} from "ai";
import superjson from "superjson";

export type DoGenerateResponseType = Awaited<
  ReturnType<LanguageModelV1["doGenerate"]>
>;

export type RemoteModelCallOptions = {
  /**
   * The maximum number of concurrent requests to the model service.
   * If not specified, there is no limit on the number of concurrent requests.
   */
  maxConcurrency?: number;
} & Omit<restate.RunOptions<DoGenerateResponseType>, "serde">;

export type RemoteModelRequest = {
  params: LanguageModelV1CallOptions;
  modelProvider: string;
  modelId: string;
  runOpts?: Omit<restate.RunOptions<DoGenerateResponseType>, "serde">;
};

export type ModelService = typeof models;

class SuperJsonSerde<T> implements restate.Serde<T> {
  contentType = "application/json";

  serialize(value: T): Uint8Array {
    const js = superjson.stringify(value);
    return new TextEncoder().encode(js);
  }

  deserialize(data: Uint8Array): T {
    const js = new TextDecoder().decode(data);
    return superjson.parse(js) as T;
  }
}

export const superJson = new SuperJsonSerde<any>();

/**
 * The following function is a middleware that provides durability to the results of a
 * `doGenerate` method of a LanguageModelV1 instance.
 * @param ctx the restate context used to capture the execution of the `doGenerate` method.
 * @param opts retry options for the `doGenerate` method.
 * @returns an LanguageModelV1Middleware that provides durability to the underlying model.
 */
export const durableCalls = (
  ctx: restate.Context,
  opts?: restate.RunOptions<DoGenerateResponseType>,
): LanguageModelV1Middleware => {
  const runOpts = {
    serde: new SuperJsonSerde<DoGenerateResponseType>(),
    ...opts,
  };

  return {
    wrapGenerate({ model, doGenerate }) {
      return ctx.run(
        `calling ${model.provider}`,
        async () => doGenerate(),
        runOpts,
      );
    },
  };
};

/**
 * Creates a middleware that allows for remote calls to a model service.
 * This middleware will use the `models` service to call the model provider and model ID specified in the request.
 * In addition, it will use the `maxConcurrency` option to limit the number of concurrent requests to the model service.
 *
 * @param ctx
 * @param opts
 * @returns
 */
export const remoteCalls = (
  ctx: restate.Context,
  opts: RemoteModelCallOptions,
): LanguageModelV1Middleware => {
  return {
    wrapGenerate({ model, params }) {
      const request = {
        modelProvider: model.provider,
        modelId: model.modelId,
        params,
        runOpts: {
          ...opts,
        },
      };

      let concurrencyKey;
      if (opts.maxConcurrency) {
        // generate a random key from the range [0, opts.maxConcurrency)
        const randomIndex = Math.floor(ctx.rand.random() * opts.maxConcurrency);
        concurrencyKey = `${model.provider}:${model.modelId}:${randomIndex}`;
      } else {
        concurrencyKey = ctx.rand.uuidv4();
      }

      return ctx
        .objectClient<ModelService>({ name: "models" }, concurrencyKey)
        .doGenerate(
          request,
          restate.rpc.opts({ input: superJson, output: superJson }),
        );
    },
  };
};

/**
 * The `models` service provides a durable way to call LLM models.
 * Use this in conjunction with the `remoteCalls` middleware.
 */
export const models = restate.object({
  name: "models",
  handlers: {
    doGenerate: restate.handlers.object.exclusive(
      {
        input: superJson,
        output: superJson,
        description: "A service to durably call LLM models",
      },
      async (
        ctx: restate.Context,
        { params, modelProvider, modelId, runOpts }: RemoteModelRequest,
      ): Promise<DoGenerateResponseType> => {
        let model;
        if (modelProvider === "openai.chat") {
          model = openai(modelId, { structuredOutputs: true });
        } else if (modelProvider === "google") {
          model = google(modelId, { structuredOutputs: true });
        } else {
          throw new restate.TerminalError(
            `Model provider ${modelProvider} is not supported.`,
          );
        }

        return await ctx.run(
          `calling ${modelProvider}`,
          async () => {
            return model.doGenerate(params);
          },
          { maxRetryAttempts: 3, ...runOpts, serde: superJson },
        );
      },
    ),
  },
});
