import * as restate from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";
import { remoteCalls } from "../ai_infra";

import { z } from "zod";

import { openai } from "@ai-sdk/openai";
import { generateObject, generateText, wrapLanguageModel } from "ai";

export default restate.service({
  name: "translation",
  handlers: {
    message: restate.handlers.handler(
      {
        input: serde.zod(
          z.object({
            text: z.string(),
            targetLanguage: z.string().default("English"),
          })
        ),
        output: serde.zod(z.string()),
      },
      async (ctx: restate.Context, { text, targetLanguage }) => {
        const { finalTranslation } = await translateWithFeedback(
          ctx,
          text,
          targetLanguage
        );
        return finalTranslation;
      }
    ),
  },
});

// https://ai-sdk.dev/docs/foundations/agents#evaluator-optimizer
async function translateWithFeedback(ctx: restate.Context, text: string, targetLanguage: string) {
  let currentTranslation = '';
  let iterations = 0;
  const MAX_ITERATIONS = 3;
  
   const gpt4oMini = wrapLanguageModel({
     model: openai("gpt-4o-mini", { structuredOutputs: true }),
     middleware: remoteCalls(ctx, { maxRetryAttempts: 3, maxConcurrency: 10 }),
   });
   
   const gpt4o = wrapLanguageModel({
     model: openai("gpt-4o", { structuredOutputs: true }),
     middleware: remoteCalls(ctx, { maxRetryAttempts: 3, maxConcurrency: 10 }),
   });

  // Initial translation
  const { text: translation } = await generateText({
    model: gpt4oMini, // use small model for first attempt
    system: 'You are an expert literary translator.',
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
      system: 'You are an expert in evaluating literary translations.',
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
      system: 'You are an expert literary translator.',
      prompt: `Improve this translation based on the following feedback:
      ${evaluation.specificIssues.join('\n')}
      ${evaluation.improvementSuggestions.join('\n')}

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

