import * as restate from "@restatedev/restate-sdk";
import { generateText, stepCountIs, tool, wrapLanguageModel } from "ai";
import { openai } from "@ai-sdk/openai";
import { durableCalls, rethrowTerminalToolError } from "@restatedev/vercel-ai-middleware";
import {
  reserveHotel,
  reserveCar,
  reserveFlight,
  confirmHotel,
  confirmCar,
  confirmFlight,
  cancelCar,
  cancelFlight,
  cancelHotel,
  CarBooking,
  CarBookingSchema,
  FlightBooking,
  FlightBookingSchema,
  HotelBooking,
  HotelBookingSchema,
} from "../utils";

// <start_here>
const book = async (ctx: restate.Context, { prompt }: { prompt: string }) => {
  const on_rollback: { (): restate.RestatePromise<any> }[] = [];

  const bookingId = ctx.rand.uuidv4();

  const model = wrapLanguageModel({
    model: openai("gpt-4o"),
    middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
  });

  try {
    const { text } = await generateText({
      model,
      system: `Book a complete travel package with the requirements in the prompt.
        Use the tools to request booking of hotels and flights.`,
      prompt,
      tools: {
        bookHotel: tool({
          description: "Book a hotel reservation",
          inputSchema: HotelBookingSchema,
          execute: async (req: HotelBooking) => {
            on_rollback.push(() => ctx.run("cancel-hotel", () => cancelHotel(bookingId)));
            return ctx.run("book-hotel", () => reserveHotel(bookingId, req));
          },
        }),
        bookFlight: tool({
          description: "Book a flight",
          inputSchema: FlightBookingSchema,
          execute: async (req: FlightBooking) => {
            on_rollback.push(() =>
                ctx.run("cancel-flight", () => cancelFlight(bookingId)),
            );
            return ctx.run("book-flight", () => reserveFlight(bookingId, req));
          },
        }),
        // ... similar for car rental ...
      },
      stopWhen: [stepCountIs(10)],
      onStepFinish: rethrowTerminalToolError,
      providerOptions: { openai: { parallelToolCalls: false } },
    });
    return text;
  } catch (error) {
    console.log("Error occurred, rolling back all bookings...");
    for (const rollback of on_rollback.reverse()) {
      await rollback();
    }
    throw error;
  }
};
// <end_here>

export default restate.service({
  name: "BookingWithRollbackAgent",
  handlers: { book },
});
