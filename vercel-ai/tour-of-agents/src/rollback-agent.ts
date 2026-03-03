import * as restate from "@restatedev/restate-sdk";
import { Context } from "@restatedev/restate-sdk";
import { generateText, stepCountIs, tool, wrapLanguageModel } from "ai";
import { openai } from "@ai-sdk/openai";
import {
  durableCalls,
  rethrowTerminalToolError,
} from "@restatedev/vercel-ai-middleware";
import {
  FlightBooking,
  FlightBookingSchema,
  HotelBooking,
  HotelBookingSchema,
} from "./utils/types";
import {
  reserveHotel,
  reserveFlight,
  cancelFlight,
  cancelHotel,
} from "./utils/utils";
import { BookingRequest } from "./utils/types";
const schema = restate.serde.schema;

// <start_here>
const book = async (ctx: Context, { id, prompt }: BookingRequest) => {
  const undo_list: { (): restate.RestatePromise<any> }[] = [];

  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  try {
    const { text } = await generateText({
      model,
      system: `Book a complete travel package with the requirements in the prompt.
        Use tools to first book the hotel, then the flight.`,
      prompt,
      tools: {
        bookHotel: tool({
          description: "Book a hotel reservation",
          inputSchema: HotelBookingSchema,
          execute: async (req: HotelBooking) => {
            undo_list.push(() => ctx.run("🏨-cancel", () => cancelHotel(id)));
            return ctx.run("🏨-book", () => reserveHotel(id, req));
          },
        }),
        bookFlight: tool({
          description: "Book a flight",
          inputSchema: FlightBookingSchema,
          execute: async (req: FlightBooking) => {
            undo_list.push(() => ctx.run("✈️-cancel", () => cancelFlight(id)));
            return ctx.run("✈️-book", () => reserveFlight(id, req));
          },
        }),
      },
      stopWhen: [stepCountIs(10)],
      onStepFinish: rethrowTerminalToolError,
      providerOptions: { openai: { parallelToolCalls: false } },
    });
    return text;
  } catch (error) {
    console.log("Rolling back bookings");
    for (const undo_step of undo_list.reverse()) {
      await undo_step();
    }
    throw error;
  }
};

const agent = restate.service({
  name: "BookingWithRollbackAgent",
  handlers: {
    book: restate.createServiceHandler({ input: schema(BookingRequest) }, book),
  },
});

restate.serve({ services: [agent] });
// <end_here>
