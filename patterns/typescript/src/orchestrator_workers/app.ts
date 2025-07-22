import * as restate from "@restatedev/restate-sdk";
import { llmCall, extractXml } from "../util/utils";
import { RestatePromise } from "@restatedev/restate-sdk";

export interface OrchestrationRequest {
  orchestratorPrompt: string;
  workerPrompt: string;
  task: string;
  llmContext?: Record<string, any>;
}

interface TaskInfo {
  type: string;
  description: string;
}

interface WorkerResult {
  type: string;
  description: string;
  result: string;
}

interface ProcessResult {
  analysis: string;
  workerResults: WorkerResult[];
}

export const flexibleOrchestrator = restate.service({
  name: "FlexibleOrchestrator",
  handlers: {
    process: async (
      ctx: restate.Context,
      req: OrchestrationRequest,
    ): Promise<ProcessResult> => {
      // Process task by breaking it down and running subtasks in parallel
      const llmContext = req.llmContext || {};

      // Step 1: Get orchestrator response
      const orchestratorInput = formatPrompt(req.orchestratorPrompt, {
        task: req.task,
        ...llmContext,
      });
      const orchestratorResponse = await ctx.run("LLM call", () =>
        llmCall(orchestratorInput),
      );

      // Parse orchestrator response
      const analysis = extractXml(orchestratorResponse, "analysis");
      const tasksXml = extractXml(orchestratorResponse, "tasks");
      const tasks = await ctx.run("parse tasks", () => parseTasks(tasksXml));

      console.log("\n=== ORCHESTRATOR OUTPUT ===");
      console.log(`\nANALYSIS:\n${analysis}`);
      console.log(`\nTASKS:\n${JSON.stringify(tasks, null, 2)}`);

      // Step 2: Process each task in parallel
      const futures = tasks.map((taskInfo) =>
        ctx.run("process task", () =>
          llmCall(
            formatPrompt(req.workerPrompt, {
              original_task: req.task,
              task_type: taskInfo.type,
              task_description: taskInfo.description,
              ...llmContext,
            }),
          ),
        ),
      );

      const workerResponses = await RestatePromise.all(futures);

      const workerResults: WorkerResult[] = workerResponses.map(
        (workerResponse, index) => ({
          type: tasks[index].type,
          description: tasks[index].description,
          result: extractXml(workerResponse, "response"),
        }),
      );

      return {
        analysis,
        workerResults,
      };
    },
  },
});

// UTILS
function parseTasks(tasksXml: string): TaskInfo[] {
  const tasks: TaskInfo[] = [];
  let currentTask: Partial<TaskInfo> = {};

  for (const line of tasksXml.split("\n")) {
    const trimmedLine = line.trim();
    if (!trimmedLine) {
      continue;
    }

    if (trimmedLine.startsWith("<task>")) {
      currentTask = {};
    } else if (trimmedLine.startsWith("<type>")) {
      currentTask.type = trimmedLine.slice(6, -7).trim();
    } else if (trimmedLine.startsWith("<description>")) {
      currentTask.description = trimmedLine.slice(12, -13).trim();
    } else if (trimmedLine.startsWith("</task>")) {
      if (currentTask.description) {
        if (!currentTask.type) {
          currentTask.type = "default";
        }
        tasks.push(currentTask as TaskInfo);
      }
    }
  }

  return tasks;
}

function formatPrompt(
  template: string,
  variables: Record<string, any>,
): string {
  try {
    return template.replace(/\{(\w+)\}/g, (match, key) => {
      if (key in variables) {
        return String(variables[key]);
      }
      throw new Error(`Missing required prompt variable: ${key}`);
    });
  } catch (error) {
    throw new Error(`Error formatting prompt: ${error}`);
  }
}

export default flexibleOrchestrator;
