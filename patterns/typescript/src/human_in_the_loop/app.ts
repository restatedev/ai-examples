import * as restate from "@restatedev/restate-sdk";
import { Context, ObjectContext } from "@restatedev/restate-sdk";
import { llmCall } from "../util/utils";

/**
 * Human-in-the-loop workflows with Restate
 *
 * This example demonstrates how to use Restate to implement a feedback loop between a human operator and the LLM.
 * The human operator sends a request, the LLM responds with the solution.
 * The same human operator (option 1 `run`) or another human operator (option 2 `run_with_promise`) can then give feedback, which triggers another LLM-based optimization step, and so on.
 *
 * This is implemented with a stateful entity called Virtual Object which keeps track of the memory and the chain of thought.
 * If the human answers one week or one month later, the session can be recovered and resumed.
 */

export const humanInTheLoopService = restate.object({
    name: "HumanInTheLoopService",
    handlers: {
        runWithPromise: async (ctx: ObjectContext, task: string): Promise<[string, any[]]> => {
            /**
             * OPTION 1: Human evaluator gives feedback via a promise.
             * This is a useful pattern when the original person requesting the task is not the one giving feedback.
             */

                // Generate the initial solution
            let result = await generate(ctx, task);

            // Store the result in memory
            let memory = (await ctx.get<any[]>("memory")) ?? [];
            memory.push(result);
            ctx.set("memory", memory);

            while (true) {
                // Durable promise that waits for human feedback
                const { id, promise } = ctx.awakeable<string>();
                await ctx.run("ask human feedback", () => askForFeedback(id));
                const humanFeedback = await promise;

                // Check if the human feedback is a PASS
                if (humanFeedback === "PASS") {
                    return [result, memory];
                }

                result = await generate(ctx, task, memory, humanFeedback);
                memory.push(result);
                ctx.set("memory", memory);
            }
        },

        run: async (ctx: ObjectContext, task: string): Promise<string> => {
            /**
             * OPTION 2: Human evaluator gives feedback by sending a new request to the same stateful session.
             * This is a useful pattern when the original person requesting the task is also the one giving feedback.
             */

            const memory = (await ctx.get<any[]>("memory")) ?? [];
            const result = await generate(ctx, task, memory);
            memory.push(result);
            ctx.set("memory", memory);

            return result;
        }
    }
});

// UTILS

async function generate(
    ctx: Context,
    task: string,
    memory: any[] = [],
    humanFeedback: string = ""
): Promise<string> {
    /**Generate and improve a solution based on feedback.*/
    const llmContext = [
        "Previous attempts:",
        ...memory.map(m => `- ${m}`),
        `\nFeedback: ${humanFeedback}`
    ].join("\n");

    const fullPrompt = llmContext ? `${llmContext}\nTask: ${task}` : `Task: ${task}`;
    const result = await ctx.run("LLM call", () => llmCall(fullPrompt));

    console.log("\n=== GENERATION START ===");
    console.log(`Generated:\n${result}`);
    console.log("=== GENERATION END ===\n");

    return result;
}

function askForFeedback(id: string): void {
    console.log("\n=== HUMAN FEEDBACK REQUIRED ===");
    console.log("Answer 'PASS' to accept the solution.");
    console.log("\n Send feedback via:");
    console.log(
        `\n curl http://localhost:8080/restate/awakeables/${id}/resolve --json '"Your feedback..."'`
    );

    // This is a placeholder for the actual feedback mechanism: maybe an email or chat message
}