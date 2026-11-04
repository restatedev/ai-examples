// 13: Enforce an application budget before a model-requested action runs.
import * as restate from "@restatedev/restate-sdk-gen";
import {agent, asyncTool} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

type BookingContext = {hotelId: string; quotedTotalCents: number; maxTotalCents: number};

const bookingAgent = agent<BookingContext>({
  model,
  maxSteps: 4,
  instructions:
    "Call bookHotel for the named demo hotel. If the tool refuses, explain that no reservation was made.",
  tools: {
    bookHotel: asyncTool({
      description: "Book the quoted demo hotel. The application supplies the authoritative price.",
      input: z.object({hotelId: z.string()}),
      *before({hotelId}, {context}) {
        if (hotelId !== context.hotelId) return "Only the quoted hotel can be booked";
        if (context.quotedTotalCents > context.maxTotalCents) return "The quote exceeds the budget";
      },
      async execute({hotelId}, {context}) {
        return {hotelId, totalCents: context.quotedTotalCents, status: "reserved", demo: true};
      },
    }),
  },
});

export const guardedBooking = restate.service({
  name: "GuardedBooking",
  handlers: {
    ask: restate.schemas(
      {
        input: z.object({
          hotelId: z.string().default("H-42"),
          quotedTotalCents: z.number().int().positive().default(12500),
          maxTotalCents: z.number().int().positive().default(10000),
        }),
        output: z.string(),
      },
      function* ({hotelId, quotedTotalCents, maxTotalCents}) {
        const question = `Book demo hotel ${hotelId} at the quoted total of $${(quotedTotalCents / 100).toFixed(2)}.`;
        const context = {hotelId, quotedTotalCents, maxTotalCents};
        const result = yield* bookingAgent.run(question, {context});
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
  },
});
