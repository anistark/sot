import markdownIt, { type MarkdownIt } from "markdown-it";
import anchor from "markdown-it-anchor";
import Prism from "prismjs";
import loadLanguages from "prismjs/components/index.js";

loadLanguages(["bash", "toml", "json"]);

const SHELLS = new Set(["sh", "bash", "shell", "zsh", "console"]);
const ALIASES: Record<string, string> = { sh: "bash", shell: "bash", zsh: "bash", console: "bash" };

export function escapeHtml(text: string): string {
  return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

/** Wrap each line of highlighted shell code so CSS can draw a `$` prompt in front. */
function shellLines(html: string): string {
  return html
    .split("\n")
    .map((line) => {
      if (!line.trim()) return `<span class="line"></span>`;
      if (line.startsWith('<span class="token comment">')) return `<span class="line">${line}</span>`;
      // The first plain word is the program being run.
      const marked = line.replace(/^([\w.@/-]+)/, '<span class="token command">$1</span>');
      return `<span class="line cmd">${marked}</span>`;
    })
    .join("\n");
}

/** A fenced code block: a small framed panel with a language label and a copy button. */
export function codeBlock(code: string, lang: string): string {
  const source = code.replace(/\n$/, "");
  const language = ALIASES[lang] ?? lang;
  const grammar = Prism.languages[language];

  if (!lang || !grammar) {
    // No language: plain terminal output, shown without a frame.
    return `<pre class="term-output">${escapeHtml(source)}</pre>\n`;
  }

  let html = Prism.highlight(source, grammar, language);
  if (SHELLS.has(lang)) html = shellLines(html);

  return [
    `<figure class="term-block" data-lang="${lang}">`,
    `<figcaption><span>${lang}</span><button type="button" class="copy" hidden>copy</button></figcaption>`,
    `<pre class="language-${language}"><code>${html}</code></pre>`,
    `</figure>\n`,
  ].join("");
}

export function createMarkdown(): MarkdownIt {
  const md = markdownIt({ html: true, linkify: true, typographer: false });

  md.options.highlight = null;
  md.renderer.rules.fence = (tokens, idx) => {
    const token = tokens[idx];
    return codeBlock(token.content, token.info.trim().split(/\s+/)[0] ?? "");
  };

  // Headings get ids and a `##` / `###` link drawn by CSS, like Markdown in a terminal.
  md.use(anchor, {
    level: [2, 3],
    permalink: anchor.permalink.linkInsideHeader({
      symbol: "",
      placement: "before",
      ariaHidden: true,
    }),
  });

  // Wide tables scroll inside their own box instead of the whole page.
  md.renderer.rules.table_open = () => `<div class="table-wrap"><table>\n`;
  md.renderer.rules.table_close = () => `</table></div>\n`;

  // Links that leave the site open in a new tab and say so.
  const defaultLinkOpen =
    md.renderer.rules.link_open ?? ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options));
  md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
    const href = String(tokens[idx].attrGet("href") ?? "");
    if (/^https?:\/\//.test(href)) {
      tokens[idx].attrSet("target", "_blank");
      tokens[idx].attrSet("rel", "noopener");
      tokens[idx].attrJoin("class", "external");
    }
    return defaultLinkOpen(tokens, idx, options, env, self);
  };

  return md;
}

export const markdown = createMarkdown();
