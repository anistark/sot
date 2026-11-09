/**
 * Builds the CSS (Tailwind), the browser script (esbuild) and the search index
 * (Pagefind) inside the Eleventy run, so `eleventy` and `eleventy --serve` are
 * the only commands needed.
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import tailwindcss from "@tailwindcss/postcss";
import * as esbuild from "esbuild";
import * as pagefind from "pagefind";
import postcss from "postcss";

const ROOT = path.resolve(import.meta.dirname, "..");
const production = () => process.env.ELEVENTY_RUN_MODE === "build";

export async function buildCss(outputDir: string): Promise<void> {
  const from = path.join(ROOT, "src/assets/css/main.css");
  const to = path.join(outputDir, "assets/main.css");
  const result = await postcss([tailwindcss({ base: ROOT, optimize: production() ? { minify: true } : false })]).process(
    await readFile(from, "utf8"),
    { from, to },
  );
  await mkdir(path.dirname(to), { recursive: true });
  await writeFile(to, result.css);
}

export async function buildJs(outputDir: string): Promise<void> {
  await esbuild.build({
    entryPoints: [path.join(ROOT, "src/assets/ts/main.ts")],
    outfile: path.join(outputDir, "assets/main.js"),
    bundle: true,
    format: "esm",
    target: "es2022",
    minify: production(),
    sourcemap: production() ? false : "inline",
    logLevel: "warning",
  });
}

export async function buildSearch(outputDir: string): Promise<void> {
  const { index, errors } = await pagefind.createIndex({});
  if (!index) throw new Error(`Pagefind could not start: ${errors.join(", ")}`);
  await index.addDirectory({ path: outputDir });
  await index.writeFiles({ outputPath: path.join(outputDir, "pagefind") });
  await pagefind.close();
}
