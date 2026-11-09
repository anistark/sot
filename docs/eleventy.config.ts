import { HtmlBasePlugin } from "@11ty/eleventy";
import type UserConfig from "@11ty/eleventy/UserConfig";
import { buildCss, buildJs, buildSearch } from "./config/assets.ts";
import { flatten, navData } from "./config/data.ts";
import { buildImages } from "./config/images.ts";
import { type DocPage, llmsFull, llmsTxt, pageMarkdown, plainText } from "./config/llms.ts";
import { markdown } from "./config/markdown.ts";
import { structuredData } from "./config/seo.ts";
import {
  configTemplate,
  helpHtml,
  itemCommand,
  keyCaps,
  keysTable,
  logoSvg,
  neighbours,
  outline,
  output,
  prompt,
  repoMarkdown,
} from "./config/terminal.ts";

// GitHub Pages serves the site from /sot/. The docs workflow sets both from the
// repository's Pages settings, so a custom domain needs no change here.
const pathPrefix = process.env.PATH_PREFIX ?? "/sot/";
const siteUrl = (process.env.SITE_URL ?? "https://anistark.github.io/sot").replace(/\/?$/, "/");
const OUTPUT = "_site";
const FONTS = "node_modules/@fontsource-variable/roboto-mono/files";

export default function (eleventyConfig: UserConfig) {
  eleventyConfig.addPlugin(HtmlBasePlugin);
  eleventyConfig.setLibrary("md", markdown);

  // The docs pages in tree order: the sitemap, llms.txt and the Markdown copies list these.
  eleventyConfig.addCollection("docs", (api: { getAll(): DocPage[] }) => {
    const order = flatten(navData().tree).map((p) => p.url);
    return api
      .getAll()
      .filter((p) => order.includes(p.url))
      .sort((a, b) => order.indexOf(a.url) - order.indexOf(b.url));
  });

  eleventyConfig.addFilter("prompt", prompt);
  eleventyConfig.addFilter("help", helpHtml);
  eleventyConfig.addFilter("keyCaps", keyCaps);
  eleventyConfig.addFilter("outline", outline);
  eleventyConfig.addFilter("neighbours", neighbours);
  eleventyConfig.addFilter("flattenNav", flatten);
  eleventyConfig.addFilter("itemCommand", itemCommand);
  eleventyConfig.addFilter("logo", logoSvg);
  eleventyConfig.addFilter("plainText", plainText);
  eleventyConfig.addFilter("md", (text: string) => markdown.render(text));
  eleventyConfig.addFilter("mdInline", (text: string) => markdown.renderInline(text));
  eleventyConfig.addFilter("pageMarkdown", (page: DocPage) => pageMarkdown(page, siteUrl));
  eleventyConfig.addFilter("llmsTxt", (pages: DocPage[]) => llmsTxt(pages, siteUrl));
  eleventyConfig.addFilter("llmsFull", (pages: DocPage[]) => llmsFull(pages, siteUrl));

  eleventyConfig.addShortcode("prompt", prompt);
  eleventyConfig.addShortcode("help", helpHtml);
  eleventyConfig.addShortcode("keysTable", keysTable);
  eleventyConfig.addShortcode("configTemplate", configTemplate);
  eleventyConfig.addShortcode("output", output);
  eleventyConfig.addShortcode("repoMarkdown", repoMarkdown);
  eleventyConfig.addShortcode("structuredData", function (this: { page: { url: string } }, title: string, description?: string) {
    return structuredData({ url: this.page.url, title, description }, siteUrl);
  });

  eleventyConfig.addPassthroughCopy({
    "../images/demo.gif": "assets/img/demo.gif",
    [`${FONTS}/roboto-mono-latin-wght-normal.woff2`]: "assets/fonts/roboto-mono-latin.woff2",
    [`${FONTS}/roboto-mono-latin-ext-wght-normal.woff2`]: "assets/fonts/roboto-mono-latin-ext.woff2",
    [`${FONTS}/roboto-mono-latin-wght-italic.woff2`]: "assets/fonts/roboto-mono-latin-italic.woff2",
  });

  // CSS, the browser script and the icons are built here rather than by separate watchers.
  eleventyConfig.addWatchTarget("src/assets/");
  eleventyConfig.addWatchTarget("../CHANGELOG.md");
  eleventyConfig.on("eleventy.before", () => Promise.all([buildCss(OUTPUT), buildJs(OUTPUT), buildImages(OUTPUT)]));
  eleventyConfig.on("eleventy.after", () => buildSearch(OUTPUT));

  eleventyConfig.addGlobalData("pathPrefix", pathPrefix);
  eleventyConfig.addGlobalData("siteUrl", siteUrl);

  // The dev server listens on every interface; print the LAN and Tailscale
  // addresses too, so the docs can be opened from a phone or another machine.
  eleventyConfig.setServerOptions({ showAllHosts: true });
}

export const config = {
  dir: { input: "src", output: OUTPUT, includes: "_includes", data: "_data" },
  pathPrefix,
  markdownTemplateEngine: "njk",
  htmlTemplateEngine: "njk",
};
