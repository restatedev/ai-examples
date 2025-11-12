import { z } from "zod";
import { serde } from "@restatedev/restate-sdk-zod";
import * as restate from "@restatedev/restate-sdk";
import llmCall from "./llm";
import {TerminalError} from "@restatedev/restate-sdk";

export function zodPrompt(examplePrompt: string) {
  return serde.zod(
    z.object({
      message: z.string().default(examplePrompt),
    }),
  );
}

export function printEvaluation(
  iteration: number,
  solution: string,
  evaluation: string,
) {
  console.log(
    `Iteration ${iteration + 1}: Solution: ${solution} Evaluation: ${evaluation}`,
  );
}

export async function fetchWeather(city: string) {
    const output = await fetchWeatherFromAPI(city);
    return parseWeatherResponse(output);
}

async function fetchWeatherFromAPI(city: string) {
    const url = `https://wttr.in/${encodeURIComponent(city)}?format=j1`;
    const res = await fetch(url);
    const output = await res.text();
    if (!res.ok) {
        if (res.status === 404 && output) {
            throw new TerminalError(
                `Unknown location: ${city}. Please provide a valid city name.`,
            );
        }
        throw new Error(`Weather API returned status ${res.status}`);
    }
    return output;
}

async function parseWeatherResponse(output: string) {
    try {
        const data = JSON.parse(output);
        const current = data.current_condition?.[0];

        if (!current) {
            throw new Error("Missing current weather data");
        }

        return {
            temperature: current.temp_C,
            description: current.weatherDesc?.[0]?.value,
        };
    } catch (e) {
        throw new TerminalError("Could not parse weather API response", {
            cause: e,
        });
    }
}

export function notifyModerator(content: string, approvalId: string): void {
  console.log("\n🔍 CONTENT MODERATION REQUIRED 🔍");
  console.log(`Content: ${content}`);
  console.log("Awaiting human decision...");
  console.log("\nTo approve:");
  console.log(
    `curl http://localhost:8080/restate/awakeables/${approvalId}/resolve --json '"approved"'`,
  );
  console.log("\nTo reject:");
  console.log(
    `curl http://localhost:8080/restate/awakeables/${approvalId}/resolve --json '"rejected"'`,
  );
}

export interface SupportTicket {
  user_id: string;
  message: string;
}

export function fetchServiceStatus(): string {
  return JSON.stringify({
    api: {
      name: "API Gateway",
      status: "operational",
      uptime_24h: 99.8,
      response_time_avg: "120ms",
      incidents: 0,
    },
    database: {
      name: "Primary Database",
      status: "operational",
      uptime_24h: 100.0,
      response_time_avg: "15ms",
      incidents: 0,
    },
    payment: {
      name: "Payment Service",
      status: "degraded",
      uptime_24h: 95.2,
      response_time_avg: "450ms",
      incidents: 1,
      incident_description:
        "Intermittent timeout issues with payment processor",
    },
    dashboard: {
      name: "User Dashboard",
      status: "operational",
      uptime_24h: 99.9,
      response_time_avg: "200ms",
      incidents: 0,
    },
    notifications: {
      name: "Email/SMS Service",
      status: "maintenance",
      uptime_24h: 98.5,
      response_time_avg: "N/A",
      incidents: 0,
      incident_description: "Scheduled maintenance until 14:00 UTC",
    },
  });
}

export function createSupportTicket(ticket: SupportTicket): string {
  const ticketId = crypto.randomUUID();
  return JSON.stringify({
    ticket_id: ticketId,
    user_id: ticket.user_id,
    status: "open",
    created_at: new Date().toISOString(),
    details: ticket.message,
  });
}

const usersDb: Record<string, any> = {
  user_12345: {
    user_id: "user_12345",
    email: "john@example.com",
    subscription: {
      plan: "Pro",
      status: "active",
      billing_cycle: "monthly",
      price: 49.99,
      next_billing: "2024-02-15",
    },
    usage: {
      api_calls_this_month: 10000,
      api_limit: 10000,
      storage_used_gb: 12.5,
      storage_limit_gb: 50,
    },
    account_status: "good_standing",
    created_date: "2023-06-15",
  },
  user_67890: {
    user_id: "user_67890",
    email: "jane@startup.com",
    subscription: {
      plan: "Enterprise",
      status: "active",
      billing_cycle: "yearly",
      price: 999.99,
      next_billing: "2024-06-01",
    },
    usage: {
      api_calls_this_month: 45000,
      api_limit: 100000,
      storage_used_gb: 180.2,
      storage_limit_gb: 1000,
    },
    account_status: "good_standing",
    created_date: "2022-01-10",
  },
};

export function queryUserDb(userId: string): string {
  const content = usersDb[userId];
  if (content) {
    return JSON.stringify(content);
  } else {
    return "User not found";
  }
}

// Billing Support Agent
export const billingAgent = restate.service({
  name: "BillingAgent",
  handlers: {
    run: async (ctx: restate.Context, question: string): Promise<string> =>
      ctx.run(
        "account_response",
        async () =>
          llmCall(`You are a billing support specialist.
            Acknowledge the billing issue, explain charges clearly, provide next steps with timeline.
            ${question}`),
        { maxRetryAttempts: 3 },
      ),
  },
});

// Account Security Agent
export const accountAgent = restate.service({
  name: "AccountAgent",
  handlers: {
    run: async (ctx: restate.Context, question: string): Promise<string> =>
      ctx.run(
        "account_response",
        async () =>
          llmCall(`You are an account security specialist.
            Prioritize account security and verification, provide clear recovery steps, include security tips.
            ${question}`),
        { maxRetryAttempts: 3 },
      ),
  },
});

// Product Support Agent
export const productAgent = restate.service({
  name: "ProductAgent",
  handlers: {
    run: async (ctx: restate.Context, question: string): Promise<string> =>
      ctx.run(
        "product_response",
        async () =>
          llmCall(`You are a product specialist.
            Focus on feature education and best practices, include specific examples, suggest related features.
            ${question}`),
        { maxRetryAttempts: 3 },
      ),
  },
});
