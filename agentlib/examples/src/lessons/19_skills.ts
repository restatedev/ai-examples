// 19: Give an agent skills from a folder.
//
// A skill is instructions for one kind of task. The model sees each skill's
// name and description, and loads a skill only when a task needs it, so an
// agent can carry many without paying for them in every request. The SDK
// takes skills from any source; this one reads a folder laid out like
// Anthropic's Agent Skills:
//
//   skills/
//     release-notes/
//       SKILL.md        <- frontmatter with name and description, then instructions
//       template.md     <- a file the instructions refer to
//     incident-summary/
//       SKILL.md
import {readdir, readFile} from "node:fs/promises";
import {join} from "node:path";
import {fileURLToPath} from "node:url";
import * as restate from "@restatedev/restate-sdk-gen";
import {agent, type SkillSource} from "@restatedev/agentlib";
import {z} from "zod";
import {exampleModel as model} from "../shared.js";

/**
 * A SKILL.md's frontmatter fields and its body. Enough YAML for skills:
 * `key: value`, quoted values, and `>` or `|` blocks on indented lines.
 */
function parseSkill(text: string) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/.exec(text);
  const fields: Record<string, string> = {};
  let block: {key: string; folded: boolean; lines: string[]} | undefined;
  const close = () => {
    if (block) fields[block.key] = block.lines.join(block.folded ? " " : "\n").trim();
    block = undefined;
  };
  for (const line of match?.[1]?.split(/\r?\n/) ?? []) {
    if (block && (/^\s/.test(line) || !line)) {
      block.lines.push(line.trim());
      continue;
    }
    close();
    const field = /^([\w-]+):\s*(.*)$/.exec(line);
    if (!field) continue;
    const [, key, value] = field as unknown as [string, string, string];
    if (/^[>|][-+]?$/.test(value)) block = {key, folded: value.startsWith(">"), lines: []};
    else fields[key] = value.trim().replace(/^(["'])(.*)\1$/, "$2");
  }
  close();
  return {fields, body: text.slice(match?.[0].length ?? 0).trim()};
}

/** Every folder with a SKILL.md is a skill; its location is the folder. */
export function folderSkills(root: string): SkillSource {
  return {
    async list() {
      const folders = await readdir(root, {withFileTypes: true});
      const skills = [];
      for (const folder of folders.filter((entry) => entry.isDirectory())) {
        const location = join(root, folder.name);
        const {fields} = parseSkill(await readFile(join(location, "SKILL.md"), "utf8"));
        skills.push({name: fields.name ?? folder.name, description: fields.description!, location});
      }
      return skills;
    },
    async load({location}) {
      return parseSkill(await readFile(join(location!, "SKILL.md"), "utf8")).body;
    },
    // The SDK has already rejected absolute paths and "..".
    async read({location}, path) {
      return readFile(join(location!, path), "utf8");
    },
  };
}

const writer = agent({
  model,
  maxSteps: 6,
  instructions: "You write for a software team. Answer with the finished text only.",
  // From src/lessons or dist/lessons alike, the package's skills folder.
  skills: folderSkills(fileURLToPath(new URL("../../skills/", import.meta.url))),
});

export const skilledWriter = restate.service({
  name: "SkilledWriter",
  handlers: {
    write: restate.schemas(
      {
        input: z.object({
          request: z
            .string()
            .default(
              "Release notes for 2.4.0: added CSV export, fixed the login redirect loop, bumped lodash.",
            ),
        }),
        output: z.string(),
      },
      function* ({request}) {
        const result = yield* writer.run(request);
        if (result.status !== "completed") return result.output ?? result.reason;
        return result.output;
      },
    ),
  },
});
