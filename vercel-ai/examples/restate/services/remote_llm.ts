import * as restate from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";

import { z } from "zod";

import { openai } from "@ai-sdk/openai";
import { generateObject, generateText, wrapLanguageModel } from "ai";
import { superJson } from "@restatedev/vercel-ai-middleware";
import {
  LanguageModelV2,
  LanguageModelV2CallOptions,
  LanguageModelV2Middleware,
} from "@ai-sdk/provider";

export const translation = restate.service({
  name: "translation",
  handlers: {
    message: restate.handlers.handler(
      {
        input: serde.zod(
          z.object({
            text: z.string(),
            targetLanguage: z.string().default("English"),
          }),
        ),
        output: serde.zod(z.string()),
      },
      async (ctx: restate.Context, { text, targetLanguage }) => {
        const { finalTranslation } = await translateWithFeedback(
          ctx,
          text,
          targetLanguage,
        );
        return finalTranslation;
      },
    ),
  },
});

// https://ai-sdk.dev/docs/foundations/agents#evaluator-optimizer
async function translateWithFeedback(
  ctx: restate.Context,
  text: string,
  targetLanguage: string,
) {
  let currentTranslation = "";
  let iterations = 0;
  const MAX_ITERATIONS = 3;

  const gpt4oMini = wrapLanguageModel({
    model: openai("gpt-4o-mini"),
    middleware: remote.remoteCalls(ctx, {
      maxRetryAttempts: 3,
      maxConcurrency: 10,
    }),
  });

  const gpt4o = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: remote.remoteCalls(ctx, {
      maxRetryAttempts: 3,
      maxConcurrency: 10,
    }),
  });

  // Initial translation
  const { text: translation } = await generateText({
    model: gpt4oMini, // use small model for first attempt
    system: "You are an expert literary translator.",
    prompt: `Translate this text to ${targetLanguage}, preserving tone and cultural nuances:
    ${text}`,
  });

  currentTranslation = translation;

  // Evaluation-optimization loop
  while (iterations < MAX_ITERATIONS) {
    // Evaluate current translation
    const { object: evaluation } = await generateObject({
      model: gpt4o, // use a larger model to evaluate
      schema: z.object({
        qualityScore: z.number().min(1).max(10),
        preservesTone: z.boolean(),
        preservesNuance: z.boolean(),
        culturallyAccurate: z.boolean(),
        specificIssues: z.array(z.string()),
        improvementSuggestions: z.array(z.string()),
      }),
      system: "You are an expert in evaluating literary translations.",
      prompt: `Evaluate this translation:

      Original: ${text}
      Translation: ${currentTranslation}

      Consider:
      1. Overall quality
      2. Preservation of tone
      3. Preservation of nuance
      4. Cultural accuracy`,
    });

    // Check if quality meets threshold
    if (
      evaluation.qualityScore >= 8 &&
      evaluation.preservesTone &&
      evaluation.preservesNuance &&
      evaluation.culturallyAccurate
    ) {
      break;
    }

    // Generate improved translation based on feedback
    const { text: improvedTranslation } = await generateText({
      model: gpt4o, // use a larger model
      system: "You are an expert literary translator.",
      prompt: `Improve this translation based on the following feedback:
      ${evaluation.specificIssues.join("\n")}
      ${evaluation.improvementSuggestions.join("\n")}

      Original: ${text}
      Current Translation: ${currentTranslation}`,
    });

    currentTranslation = improvedTranslation;
    iterations++;
  }

  return {
    finalTranslation: currentTranslation,
    iterationsRequired: iterations,
  };
}

export namespace remote {
  export type DoGenerateResponseType = Awaited<
    ReturnType<LanguageModelV2["doGenerate"]>
  >;

  export type RemoteModelCallOptions = {
    /**
     * The maximum number of concurrent requests to the model service.
     * If not specified, there is no limit on the number of concurrent requests.
     */
    maxConcurrency?: number;
  } & Omit<restate.RunOptions<DoGenerateResponseType>, "serde">;

  export type RemoteModelRequest = {
    params: LanguageModelV2CallOptions;
    modelProvider: string;
    modelId: string;
    runOpts?: Omit<restate.RunOptions<DoGenerateResponseType>, "serde">;
  };

  export type ModelService = typeof models;

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
  ): LanguageModelV2Middleware => {
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
          const randomIndex = Math.floor(
            ctx.rand.random() * opts.maxConcurrency,
          );
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
            model = openai(modelId);
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
}
