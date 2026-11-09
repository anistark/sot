/**
 * Plain Markdown for agents and LLMs, following https://llmstxt.org:
 *
 * - every page also exists as Markdown at its URL + `index.html.md`
 * - /llms.txt lists them with a one-line summary each
 * - /llms-full.txt is every page in one file
 *
 * The Markdown comes from the same page sources, with the shortcodes turned
 * into Markdown (help output and tables as code blocks and Markdown tables).
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { keyLabels } from "./terminal.ts";
import {
  DOCS_ROOT,
  type NavItem,
  configPathOutput,
  flatten,
  installSnippet,
  navData,
  overviewData,
  repoMarkdownSource,
  siteData,
  sotData,
} from "./data.ts";

export interface DocPage {
  url: string;
  inputPath: string;
  data: { title: string; description?: string; cmds?: string[] };
}

/** Markdown and inline code removed, for meta descriptions and one-line summaries. */
export function plainText(text: string | undefined): string {
  return (text ?? "")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\*\*([^*]*)\*\*/g, "$1");
}

export const absoluteUrl = (siteUrl: string, url: string) => siteUrl + url.replace(/^\//, "");

/** The Markdown copy of a page: `/install/` → `<site>/install/index.html.md`. */
export function markdownUrl(siteUrl: string, url: string): string {
  const [pathname, fragment] = url.split("#");
  const file = pathname.endsWith("/") ? `${pathname}index.html.md` : pathname;
  return absoluteUrl(siteUrl, file) + (fragment ? `#${fragment}` : "");
}

const helpCommand = (c: string) => (c === "sot" ? "sot --help" : `sot ${c} --help`);

function keysMarkdown(): string {
  const keys = sotData()?.keys ?? [];
  const label = (k: string) => keyLabels(k).map((l) => `\`${l}\``).join(" ");
  return ["| Id | Keys | Action |", "| --- | --- | --- |", ...keys.map((b) => `| \`${b.id}\` | ${label(b.key)} | ${b.description} |`)].join(
    "\n",
  );
}

/** A Markdown block on its own, with blank lines around it. */
const block = (text: string) => `\n\n${text}\n\n`;

/** A page source with its front matter removed and every shortcode rendered as Markdown. */
function resolve(source: string, siteUrl: string): string {
  const version = sotData()?.version ?? "";
  const out = source
    .replace(/^---\n[\s\S]*?\n---\n/, "")
    .replace(/\{%\s*prompt\s+"([^"]+)"\s*%\}/g, (_, command: string) => block("```sh\n" + command + "\n```"))
    .replace(/\{%\s*keysTable\s*%\}/g, () => block(keysMarkdown()))
    .replace(/\{%\s*configTemplate\s*%\}/g, () => block("```text\n" + (configPathOutput() ?? "") + "\n```"))
    .replace(/\{%\s*repoMarkdown\s+"([^"]+)"\s*%\}/g, (_, file: string) => repoMarkdownSource(file).trim())
    .replace(/\{\{\s*sot\.version\s*\}\}/g, version)
    // Links between pages point at the other pages' Markdown copies.
    .replace(/\]\((\/[^)\s]*)\)/g, (_, url: string) => `](${markdownUrl(siteUrl, url)})`)
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  if (out.includes("{%")) throw new Error(`llms: a Nunjucks tag has no Markdown version yet:\n${out.match(/\{%.*?%\}/)?.[0]}`);
  return out;
}

function homeMarkdown(siteUrl: string): string {
  const overview = overviewData();
  return [
    ...overview.intro,
    "## Install",
    "macOS and Linux, one line (installs Python 3.10+ and pipx if missing), or your package manager of choice. On Windows, use `uv` or `pipx`.",
    installSnippet(),
    "## One app, six views",
    "Every command that opens a screen opens the same app on a different view, so you can hop between them with the number keys.",
    ["| Key | View | Shows |", "| --- | --- | --- |", ...overview.views.map((v) => `| \`${v.key}\` | ${v.name} | ${v.shows} |`)].join("\n"),
    "## Commands",
    [
      "| Command | What it does |",
      "| --- | --- |",
      ...overview.commands.map((c) => `| [\`${c.command}\`](${markdownUrl(siteUrl, c.url)}) | ${c.does} |`),
    ].join("\n"),
  ].join("\n\n");
}

/** One page as Markdown: title, summary, link to the page, `--help` output, then the page. */
export function pageMarkdown(page: DocPage, siteUrl: string): string {
  const { title, description, cmds = [] } = page.data;
  const parts = [`# ${title === "sot" && page.url === "/" ? "sot: a system monitor for the terminal" : title}`];
  if (description) parts.push(`> ${description}`);
  else if (page.url === "/") parts.push(`> ${siteData().description}`);
  parts.push(`Web page: ${absoluteUrl(siteUrl, page.url)}`);

  const sot = sotData();
  for (const c of cmds) {
    const help = sot?.commands[c]?.help;
    if (help) parts.push(`## \`${helpCommand(c)}\``, "```text\n" + help + "\n```");
  }

  if (page.url === "/") parts.push(homeMarkdown(siteUrl));
  else parts.push(resolve(readFileSync(path.resolve(DOCS_ROOT, page.inputPath), "utf8"), siteUrl));
  return parts.join("\n\n") + "\n";
}

function entry(page: DocPage | undefined, item: NavItem, siteUrl: string): string {
  const title = item.url === "/" ? "Overview" : (page?.data.title ?? item.title);
  const summary = page?.data.description ?? (item.url === "/" ? "What sot is, how to install it, the six views and every command" : "");
  return `- [${title}](${markdownUrl(siteUrl, item.url)})${summary ? `: ${summary}` : ""}`;
}

/** /llms.txt: what sot is, then every page with a one-line summary. */
export function llmsTxt(pages: DocPage[], siteUrl: string): string {
  const site = siteData();
  const sot = sotData();
  const byUrl = new Map(pages.map((p) => [p.url, p]));
  const nav = navData();

  const sections: string[] = [];
  const docs = nav.tree.filter((e): e is NavItem => !("dir" in e) && !e.optional);
  sections.push("## Docs", docs.map((item) => entry(byUrl.get(item.url), item, siteUrl)).join("\n"));
  for (const dir of nav.tree.filter((e) => "dir" in e)) {
    sections.push(
      `## ${dir.dir[0].toUpperCase()}${dir.dir.slice(1)}`,
      dir.children.map((item) => entry(byUrl.get(item.url), item, siteUrl)).join("\n"),
    );
  }
  const optional = nav.tree.filter((e): e is NavItem => !("dir" in e) && Boolean(e.optional));
  sections.push(
    "## Optional",
    [
      ...optional.map((item) => entry(byUrl.get(item.url), item, siteUrl)),
      `- [All docs in one file](${siteUrl}llms-full.txt): Every page above, in one Markdown file`,
      `- [Source code](${site.repo}): The GitHub repository, with the issue tracker`,
      "- [PyPI](https://pypi.org/project/sot/): Releases and install metadata",
    ].join("\n"),
  );

  return [
    `# sot`,
    `> ${site.description}`,
    [
      "Install with `uv tool install sot`, `pipx install sot` or `brew install anistark/tools/sot`; it needs Python 3.10 or newer.",
      sot ? `These docs are for sot ${sot.version}.` : "",
      "The `--help` output, key bindings and config template in them are generated from sot's own code, so they match the release.",
    ]
      .filter(Boolean)
      .join(" "),
    ...sections,
  ].join("\n\n") + "\n";
}

/** /llms-full.txt: every page's Markdown, in tree order. */
export function llmsFull(pages: DocPage[], siteUrl: string): string {
  const site = siteData();
  const order = flatten(navData().tree).map((p) => p.url);
  const sorted = [...pages].sort((a, b) => order.indexOf(a.url) - order.indexOf(b.url));
  return [`# sot documentation\n\n> ${site.description}`, ...sorted.map((p) => pageMarkdown(p, siteUrl).trim())].join("\n\n---\n\n") + "\n";
}
