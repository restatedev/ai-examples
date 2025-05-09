import * as restate from "@restatedev/restate-sdk";
import { z } from "zod";
declare const ToolResponse: z.ZodObject<{
    content: z.ZodArray<z.ZodObject<{
        type: z.ZodString;
        text: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        type: string;
        text: string;
    }, {
        type: string;
        text: string;
    }>, "many">;
}, "strip", z.ZodTypeAny, {
    content: {
        type: string;
        text: string;
    }[];
}, {
    content: {
        type: string;
        text: string;
    }[];
}>;
export type ToolResponse = z.infer<typeof ToolResponse>;
export declare function tool<I extends z.ZodType>(opts: {
    description: string;
    input: I;
}, fn: (ctx: restate.Context, input: z.infer<I>) => Promise<ToolResponse>): typeof fn;
export {};
//# sourceMappingURL=api.d.ts.map