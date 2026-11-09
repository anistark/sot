/**
 * Filters and shortcodes that draw terminal pieces: prompts, `--help` output,
 * key caps, the sot logo and the page outline.
 */
import { type Binding, type NavEntry, type NavItem, configPathOutput, flatten, repoMarkdownSource, sotData } from "./data.ts";
import { escapeHtml, markdown } from "./markdown.ts";

/** A shell prompt line: `~/sot ❯ <command>`. `typed` plays a short typing animation. */
export function prompt(command: string, typed = false): string {
  const chars = [...command].length;
  return [
    `<div class="prompt${typed ? " typed" : ""}" data-pagefind-ignore>`,
    `<span class="cwd">~/sot</span>`,
    `<span class="sym" aria-hidden="true">❯</span>`,
    `<span class="cmd" style="--n:${chars}">${escapeHtml(command)}</span>`,
    `</div>`,
  ].join("");
}

/** Colour argparse `--help` output the way a modern shell theme would. */
export function helpHtml(text: string): string {
  const flags = (s: string) =>
    s.replace(/(^|[\s[,(|])(--?[A-Za-z][\w-]*)/g, '$1<span class="flag">$2</span>');
  const metavars = (s: string) => s.replace(/\b([A-Z][A-Z_]{1,})\b/g, '<span class="meta">$1</span>');
  const choices = (s: string) => s.replace(/(\{[\w,]+\})/g, '<span class="choice">$1</span>');

  let section = "";
  let inUsage = false;

  const lines = escapeHtml(text)
    .split("\n")
    .map((line) => {
      if (!line.trim()) {
        inUsage = false;
        return line;
      }
      if (line.startsWith("usage: ")) {
        inUsage = true;
        const rest = line
          .slice(7)
          .replace(/^(sot(?: (?![-[{])\S+)?)/, '<span class="prog">$1</span>');
        return `<span class="head">usage:</span> ${choices(metavars(flags(rest)))}`;
      }
      if (inUsage) return choices(metavars(flags(line)));

      const header = line.match(/^([a-z][\w ]*):(.*)$/);
      if (header) {
        section = header[1];
        return `<span class="head">${header[1]}:</span>${choices(header[2])}`;
      }

      // "  --flag, -f META   Description": colour the left column, keep the text plain.
      const option = line.match(/^(\s+)(-\S.*?)(\s{2,})(.*)$/) ?? line.match(/^(\s+)(-\S.*)()()$/);
      if (option) {
        const [, indent, left, gap, description] = option;
        return `${indent}${choices(metavars(flags(left)))}${gap}${flags(description)}`;
      }

      if (section === "commands") {
        const command = line.match(/^(\s+)([a-z][\w-]*)(\s{2,})(.*)$/);
        if (command) {
          const [, indent, name, gap, description] = command;
          return `${indent}<span class="prog">${name}</span>${gap}${flags(description)}`;
        }
      }
      return line;
    });

  // Newlines become entities so the block survives inside Markdown as one HTML line.
  return `<pre class="term-output help">${lines.join("&#10;")}</pre>`;
}

const KEY_NAMES: Record<string, string> = {
  escape: "Esc",
  enter: "Enter",
  space: "Space",
  tab: "Tab",
  slash: "/",
  question_mark: "?",
  plus: "+",
  minus: "-",
  equals_sign: "=",
  up: "↑",
  down: "↓",
  left: "←",
  right: "→",
  pageup: "PgUp",
  pagedown: "PgDn",
  home: "Home",
  end: "End",
  ctrl: "Ctrl",
  shift: "Shift",
};

/** Textual key names (`pagedown,ctrl+d`) as readable labels: ["PgDn", "Ctrl+D"]. */
export function keyLabels(keys: string): string[] {
  return keys.split(",").map((key) =>
    key
      .split("+")
      .map((part) => KEY_NAMES[part] ?? (part.length === 1 ? part : part[0].toUpperCase() + part.slice(1)))
      .join("+"),
  );
}

/** Textual key names as key caps. */
export function keyCaps(keys: string): string {
  return keyLabels(keys)
    .map((label) => `<kbd>${escapeHtml(label)}</kbd>`)
    .join(" ");
}

/** The table `sot --keys` prints, as an HTML table. */
export function keysTable(): string {
  const bindings: Binding[] | undefined = sotData()?.keys;
  if (!bindings?.length) return missingData("sot --keys");
  const rows = bindings
    .map(
      (b) =>
        `<tr><td><code>${escapeHtml(b.id)}</code></td><td>${keyCaps(b.key)}</td><td>${escapeHtml(b.description)}</td></tr>`,
    )
    .join("");
  return `<div class="table-wrap"><table class="keys-table"><thead><tr><th>Id</th><th>Keys</th><th>Action</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

/** What `sot --config-path` prints before the config file exists. */
export function configTemplate(): string {
  return output(configPathOutput(), "sot --config-path");
}

/** Plain output text, kept on one HTML line so it can sit inside Markdown. */
export function output(text: string | undefined, label = "this output"): string {
  if (!text) return missingData(label);
  return `<pre class="term-output">${escapeHtml(text).replaceAll("\n", "&#10;")}</pre>`;
}

export function missingData(what: string): string {
  return `<pre class="term-output missing">zsh: ${escapeHtml(what)}: no data. Run <code>just docs-data</code> to generate it from sot.</pre>`;
}

// Which quadrants of a character cell each block glyph fills: [top-left, top-right, bottom-left, bottom-right].
export const QUADRANTS: Record<string, [number, number, number, number]> = {
  "▀": [1, 1, 0, 0],
  "▄": [0, 0, 1, 1],
  "█": [1, 1, 1, 1],
  "▌": [1, 0, 1, 0],
  "▐": [0, 1, 0, 1],
  "▖": [0, 0, 1, 0],
  "▗": [0, 0, 0, 1],
  "▘": [1, 0, 0, 0],
  "▝": [0, 1, 0, 0],
  "▙": [1, 0, 1, 1],
  "▛": [1, 1, 1, 0],
  "▜": [1, 1, 0, 1],
  "▟": [0, 1, 1, 1],
  "▚": [1, 0, 0, 1],
  "▞": [0, 1, 1, 0],
};

export interface LogoGeometry {
  /** Filled quadrants as [x, y] in units: a character cell is 2 units wide and 4 tall. */
  quadrants: [number, number][];
  width: number;
  height: number;
}

/** Where sot's block-character logo has ink, one 1×2-unit quadrant at a time. */
export function logoGeometry(lines: string[]): LogoGeometry {
  const rows = lines.map((line) => [...line]);
  const start = Math.min(...rows.map((r) => r.findIndex((c) => c.trim() !== "")).filter((i) => i >= 0));
  const end = Math.max(...rows.map((r) => r.length - [...r].reverse().findIndex((c) => c.trim() !== "")));
  const quadrants: [number, number][] = [];
  rows.forEach((row, y) => {
    row.slice(start, end).forEach((char, x) => {
      QUADRANTS[char]?.forEach((on, i) => {
        if (on) quadrants.push([x * 2 + (i % 2), y * 4 + Math.floor(i / 2) * 2]);
      });
    });
  });
  return { quadrants, width: (end - start) * 2, height: rows.length * 4 };
}

/** The logo's quadrants as SVG rects, slightly oversized so neighbours don't show hairline gaps. */
export function logoRects(geometry: LogoGeometry): string {
  return geometry.quadrants.map(([x, y]) => `<rect x="${x}" y="${y}" width="1.04" height="2.04"/>`).join("");
}

/**
 * Draw sot's block-character logo as an SVG. The web font has no block
 * glyphs, so drawing it keeps the shapes crisp and the cells square.
 */
export function logoSvg(lines: string[] | undefined, className = "logo"): string {
  if (!lines?.length) return "";
  const geometry = logoGeometry(lines);
  const id = `grad-${className.replace(/\W+/g, "-")}`;
  // One gradient across the whole logo, not one per rect.
  const gradient = `<linearGradient id="${id}" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="${geometry.width}" y2="0"><stop offset="0" style="stop-color:var(--grad-a)"/><stop offset=".5" style="stop-color:var(--grad-b)"/><stop offset="1" style="stop-color:var(--grad-c)"/></linearGradient>`;
  return `<svg class="${className}" viewBox="0 0 ${geometry.width} ${geometry.height}" role="img" aria-label="sot" shape-rendering="crispEdges"><defs>${gradient}</defs><g fill="url(#${id})">${logoRects(geometry)}</g></svg>`;
}

export interface OutlineEntry {
  id: string;
  text: string;
  level: number;
}

/** The headings of a rendered page, for the outline pane. */
export function outline(html: string | undefined, depth = 2): OutlineEntry[] {
  if (!html) return [];
  const entries: OutlineEntry[] = [];
  for (const match of html.matchAll(/<h([23]) id="([^"]+)"[^>]*>(.*?)<\/h\1>/gs)) {
    const level = Number(match[1]);
    if (level > depth) continue;
    const text = match[3]
      .replace(/<a class="header-anchor"[^>]*>.*?<\/a>/s, "")
      .replace(/<[^>]+>/g, "")
      .replaceAll("&amp;", "&")
      .replaceAll("&lt;", "<")
      .replaceAll("&gt;", ">")
      .replaceAll("&quot;", '"')
      .trim();
    entries.push({ id: match[2], text, level });
  }
  return entries;
}

/** The command a page "runs" in its prompt: `sot clean --help`, or `cat install.md`. */
export function itemCommand(item: NavItem | undefined): string {
  if (!item) return "";
  return item.command ?? `cat ${item.title}.md`;
}

export function neighbours(tree: NavEntry[], url: string): { prev?: NavItem; next?: NavItem } {
  const pages = flatten(tree);
  const i = pages.findIndex((p) => p.url === url);
  if (i < 0) return {};
  return { prev: pages[i - 1], next: pages[i + 1] };
}

/** Render a Markdown file from the repository root, dropping its `# Title`. */
export function repoMarkdown(file: string): string {
  return markdown.render(repoMarkdownSource(file));
}
