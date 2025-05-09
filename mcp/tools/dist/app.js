"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const restate = __importStar(require("@restatedev/restate-sdk"));
const zod_1 = require("zod");
const api_1 = require("./api");
const greet = (0, api_1.tool)({
    description: "Greets a person by name",
    input: zod_1.z.object({ name: zod_1.z.string() }),
}, async (ctx, { name }) => {
    const seen = await ctx.objectClient(personObject, name).increment();
    return {
        content: [
            {
                type: "text",
                text: `Hello, ${name} at the ${seen}th time !`,
            },
        ],
    };
});
const personObject = restate.object({
    name: "person",
    handlers: {
        /**
         * This isn't a tool, but restate's virtual object!
         *
         * With it you can store data and create handlers that can be called from other tools.
         *
         * These objects are keyed and keep state isolated per-key.
         *
         * You can use them for:
         *
         * - Storing session data
         * - Remembering important context *per user* (key)
         * - Coordinating complex workflows
         * - And more!
         *
         * @param ctx this object's context
         * @returns the number of times the person has been seen
         */
        increment: async (ctx) => {
            const seen = (await ctx.get("seenCount")) ?? 0;
            ctx.set("seenCount", seen + 1);
            return seen;
        },
    },
});
// Create a service that binds the tool to the virtual object
const tools = restate.service({
    name: "tools",
    handlers: {
        greet,
    },
});
restate.endpoint()
    .bind(tools)
    .bind(personObject)
    .listen();
//# sourceMappingURL=app.js.map