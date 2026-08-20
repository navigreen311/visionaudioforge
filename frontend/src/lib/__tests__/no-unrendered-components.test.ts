/**
 * No component file that nothing imports, and no hand-silenced import.
 *
 * The console reached 338 component files, 134 of which no file imported - about
 * 40% of the tree, roughly 36,000 lines that had never run. Two things kept it
 * invisible: an unimported file produces no warning at all, and a file that *is*
 * imported but never placed in the tree was silenced by hand:
 *
 *     // Suppress unused-variable warnings for dynamic imports that are wired
 *     // but not yet rendered
 *     void PatrolModePanel;
 *     void ConversationHistory;
 *
 * That cost real time. An e2e journey was written against controls belonging to
 * `AudioTransformStudio`, a 1,020-line panel the transform page imported and
 * never rendered, and sat `fixme` for a round describing a collapsed section
 * that existed on no page.
 *
 * ## Why this checks imports rather than JSX
 *
 * The obvious test - "does `<Name` appear anywhere?" - is wrong, and wrongly
 * deleting ten working components is how that was discovered. `OperationControls`
 * renders its children through a lookup table:
 *
 *     const CONTROLS = {
 *       background_remove: BackgroundRemoveControls,
 *       super_resolution: SuperResolutionControls,
 *       ...
 *     };
 *
 * No `<BackgroundRemoveControls` exists anywhere, and the component is rendered
 * on every visit to the transform page. Aliased imports break the JSX check too:
 * `import DetectionTabComponent from ".../DetectionTab"` renders as
 * `<DetectionTabComponent`.
 *
 * An import, by contrast, is necessary for *any* render path. So this asserts the
 * property that can actually be verified: every component file is imported by
 * something. A file that is imported but never rendered is not detectable
 * statically with confidence - the `void` check below catches the one form of it
 * that announces itself.
 */

import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const SRC = path.resolve(__dirname, "../..");
const COMPONENTS = path.join(SRC, "components");

/**
 * Component files nothing imports, kept on purpose.
 *
 * Each entry needs a reason. "We might use it later" is not one - that is what
 * git history is for, and 134 files were removed on exactly that argument. See
 * docs/removed-unrendered-ui.md.
 */
const ALLOWED = new Map<string, string>([
  // (empty - every component file is imported by something)
]);

function sourceFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(full);
    if (!entry.isFile()) return [];
    return full.endsWith(".ts") || full.endsWith(".tsx") ? [full] : [];
  });
}

const posix = (file: string) => file.replace(/\\/g, "/");

const isTestFile = (file: string) =>
  posix(file).includes("__tests__") || /\.(test|spec)\.tsx?$/.test(file);

describe("the component tree matches the app", () => {
  const sources = sourceFiles(SRC).map((file) => ({
    file,
    text: fs.readFileSync(file, "utf8"),
  }));

  it("imports every component file it defines", () => {
    const unimported: string[] = [];

    for (const { file } of sources) {
      if (!file.startsWith(COMPONENTS) || isTestFile(file)) continue;

      const stem = path.basename(file, path.extname(file));
      if (ALLOWED.has(stem)) continue;

      // A barrel is imported by its *directory* - `from "./operations"` - so
      // match the folder name for an index file and the filename otherwise.
      const isBarrel = stem === "index";
      const target = isBarrel ? path.basename(path.dirname(file)) : stem;
      const escaped = target.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

      // Any importer names the module path, whatever alias it binds locally and
      // however it renders it: `from ".../Target"` or `import(".../Target")`.
      const imported = new RegExp(
        `(from|import\\()\\s*["'][^"']*[/"']${escaped}["']`,
      );

      if (!sources.some((other) => other.file !== file && imported.test(other.text))) {
        unimported.push(posix(path.relative(SRC, file)));
      }
    }

    expect(
      unimported,
      "No file imports these components, so nothing can render them. Import and " +
        "render one, delete it, or add it to ALLOWED with a reason:\n  " +
        unimported.join("\n  "),
    ).toEqual([]);
  });

  it("has no `void Component;` lint suppressions", () => {
    const offenders: string[] = [];

    for (const { file, text } of sources) {
      if (isTestFile(file)) continue;
      for (const match of text.matchAll(/^\s*void\s+([A-Z]\w*)\s*;/gm)) {
        offenders.push(`${match[1]}  (${posix(path.relative(SRC, file))})`);
      }
    }

    expect(
      offenders,
      "`void Component;` silences the unused-variable warning for an import that " +
        "is never rendered, which makes the tree look wired when it is not. " +
        "Render it or remove the import:\n  " +
        offenders.join("\n  "),
    ).toEqual([]);
  });
});
