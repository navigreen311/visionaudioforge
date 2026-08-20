/**
 * No panel that shows records it invented.
 *
 * `IncidentView` rendered three incidents from a `MOCK_INCIDENTS` constant, on
 * the alerts page, in production, while every endpoint it needed already
 * existed. It looked exactly like a working screen - which is the whole problem:
 * fabricated data is indistinguishable from real data in a screenshot, in a
 * demo, and in every assertion that only checks the page renders.
 *
 * The e2e sweep asserts each page asks the API for something, and that catches a
 * page built entirely from constants. It cannot catch this, because a page is
 * not the unit: `/alerts` calls the API for its inbox and its rules, so it
 * passes while its Evidence and Chain of Custody tabs are literals. The unit is
 * the panel.
 *
 * ## The rule
 *
 * A module-level literal holding *records* - an array of objects, or an object
 * containing one - that a component seeds React state with, directly or through
 * a helper.
 *
 * State is the discriminator, and a sharp one. The console is full of honest
 * module-level record literals: tab lists, dropdown options, tool palettes,
 * presets. Not one of them is state, because none of them ever changes. A
 * constant seeded into state is standing in for something that was meant to
 * arrive and never did - which is exactly what a fabricated panel is.
 *
 * An earlier version of this test also flagged any such literal *rendered*, and
 * reported 40 offenders of which 35 were option lists. A guard nobody can read
 * the output of is not a guard.
 *
 * This is deliberately not a search for the word "MOCK". Naming is a convention
 * and conventions lapse; the shape is what makes it a fake, so the shape is what
 * is matched. Renaming `MOCK_BUNDLES` to `bundles` does not make it real and
 * does not evade this test.
 *
 * ## What is allowed
 *
 * Two things look like this and are not fabrications, so they are listed in
 * ALLOWED with a reason each:
 *
 *  - a control schema (`AUGMENTATION_TYPES`) - the panel's own configuration,
 *    which nothing on the server is supposed to supply
 *  - a zeroed skeleton (`defaultStats`) - shape without content, showing "0
 *    active streams" until the real number lands. A skeleton is honest; a
 *    skeleton with invented numbers in it is not, and that difference is the
 *    line this test draws.
 */

import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const SRC = path.resolve(__dirname, "../..");

/**
 * Literals that look like seeded records but are not fabricated platform data.
 *
 * Key is `ConstantName` or `file:ConstantName`. Every entry needs a reason -
 * "it's fine" is not one. Five panels were caught by this rule the day it was
 * written; the cost of a lax exception here is that the sixth is not.
 */
const ALLOWED = new Map<string, string>([
  [
    "AUGMENTATION_TYPES",
    "The builder's own control schema: which augmentation controls to offer and " +
      "what their parameters are called. The server supplies audio, not a list " +
      "of knobs. Pinned against the API by backend/tests/test_console_api_contract.py.",
  ],
  [
    "defaultStats",
    "A zeroed skeleton - every value is 0 and every sparkline empty - so the " +
      "dashboard shows its shape before the counts arrive rather than jumping. " +
      "It states no fact that is not true.",
  ],
]);

function sourceFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(full);
    if (!entry.isFile()) return [];
    return full.endsWith(".tsx") ? [full] : [];
  });
}

const posix = (file: string) => file.replace(/\\/g, "/");

const isTestFile = (file: string) =>
  posix(file).includes("__tests__") || /\.(test|spec)\.tsx?$/.test(file);

/** Module-level constants whose value is a collection of records. */
function recordLiterals(text: string): string[] {
  const names: string[] = [];

  // `const NAME[: Type] = [ { ... } ]` - a list of records.
  for (const m of text.matchAll(/^const\s+([A-Za-z_$][\w$]*)(?:\s*:\s*[^=]+)?\s*=\s*\[/gm)) {
    if (/^\s*\{/.test(text.slice(m.index! + m[0].length, m.index! + m[0].length + 400))) {
      names.push(m[1]);
    }
  }

  // `const NAME[: Type] = { ... key: [ { ... } ] ... }` - a record that carries
  // a list of records. `MOCK_FEDERATION` was this: one federation object with a
  // participants array inside it.
  for (const m of text.matchAll(/^const\s+([A-Za-z_$][\w$]*)(?:\s*:\s*[^=]+)?\s*=\s*\{/gm)) {
    const body = text.slice(m.index! + m[0].length, m.index! + m[0].length + 1500);
    if (/\w+\s*:\s*\[\s*\{/.test(body)) names.push(m[1]);
  }

  return [...new Set(names)];
}

describe("panels show data the platform gave them", () => {
  const files = sourceFiles(SRC).filter((f) => !isTestFile(f));

  it("has no component that displays records it made up", () => {
    const offenders: string[] = [];

    for (const file of files) {
      const text = fs.readFileSync(file, "utf8");
      const relative = posix(path.relative(SRC, file));

      for (const name of recordLiterals(text)) {
        if (ALLOWED.has(name) || ALLOWED.has(`${relative}:${name}`)) continue;

        const esc = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

        // Seeded into state: `useState(NAME)`, `useState<T>(NAME)`, `useState([...NAME])`.
        //
        // State is the discriminator, and it is a sharp one. A list of tabs, an
        // options array, a tool palette - the console is full of module-level
        // record literals that are perfectly honest, and not one of them is
        // *state*, because none of them ever changes. A constant seeded into
        // state is a stand-in for something that was supposed to arrive and
        // did not.
        //
        // The gap before the paren is `[^(]*` rather than `(?:<[^>]*>)?`: a
        // generic argument nests, and `useState<Record<string, Slot | null>>(x)`
        // ends the inner `[^>]*` at the wrong angle bracket. A type argument
        // never contains a `(`, so "anything up to the opening paren" is both
        // simpler and right.
        const seedsState = new RegExp(
          `useState[^(]*\\(\\s*(?:\\[\\s*)?(?:\\.\\.\\.)?${esc}\\b`,
        ).test(text);

        // One hop of indirection. `ShiftScheduleGrid` never wrote
        // `useState(MOCK_REVIEWERS)` - it wrote `useState(buildInitialSchedule())`
        // and built the grid out of the constant inside that function, which is
        // the same fabrication with a helper in front of it.
        const viaHelper = [
          ...text.matchAll(/^function\s+([A-Za-z_$][\w$]*)[\s\S]*?^\}/gm),
        ].some(
          (fn) =>
            new RegExp(`\\b${esc}\\b`).test(fn[0]) &&
            // `useState(build)` as well as `useState(build())` - React takes a
            // lazy initialiser, and ShiftScheduleGrid used exactly that form.
            new RegExp(`useState[^(]*\\(\\s*${fn[1]}\\b`).test(text),
        );

        if (seedsState || viaHelper) {
          const how = seedsState ? "seeds state" : "seeds state via a helper";
          offenders.push(`${name}  (${relative}, ${how})`);
        }
      }
    }

    expect(
      offenders,
      "These panels display records defined in their own source. Whatever they " +
        "show is invented, and it is indistinguishable from real data on screen. " +
        "Fetch it from the API, or add it to ALLOWED with a reason:\n  " +
        offenders.join("\n  "),
    ).toEqual([]);
  });

  it("has no component left promising a call it never makes", () => {
    // The companion tell. Every panel caught above carried a comment saying
    // which endpoint it would use "in production" - the endpoint existed, and
    // the comment was the closest thing to a bug report anyone wrote.
    const offenders: string[] = [];

    for (const file of files) {
      const text = fs.readFileSync(file, "utf8");
      for (const m of text.matchAll(/^\s*\/\/\s*In production[:,].*$/gm)) {
        offenders.push(`${posix(path.relative(SRC, file))}: ${m[0].trim()}`);
      }
    }

    expect(
      offenders,
      "`// In production: ...` marks a call the component describes and does " +
        "not make. Make it, or delete the comment and the pretence:\n  " +
        offenders.join("\n  "),
    ).toEqual([]);
  });
});
