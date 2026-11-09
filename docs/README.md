# sot docs

The source of [anistark.github.io/sot](https://anistark.github.io/sot/): [Eleventy](https://www.11ty.dev/) 3, Tailwind CSS 4 and TypeScript, styled as a terminal. `.github/workflows/docs.yml` builds it and publishes it to GitHub Pages on every push to `main`.

## Run it

Needs Node.js 22.18 or newer (`.nvmrc` pins the version CI uses) and, for the generated data, the repo's `uv` setup. From the repository root:

```sh
just docs-dev      # http://localhost:8080/sot/ with live reload
just docs-build    # docs/_site, as CI builds it
```

Or by hand, from `docs/`:

```sh
uv run python ../scripts/build_docs_data.py
npm install
npm run dev        # or: npm run build, npm run check
```

## How it fits together

```
docs/
├── eleventy.config.ts     Eleventy setup; Node runs the TypeScript directly
├── config/
│   ├── data.ts            the nav, site and sot data every part reads
│   ├── markdown.ts        markdown-it: heading anchors, framed code blocks, $ prompts
│   ├── terminal.ts        prompts, coloured --help output, key caps, the logo, outline
│   ├── llms.ts            llms.txt, llms-full.txt and each page as Markdown
│   ├── seo.ts             schema.org structured data
│   ├── images.ts          favicons and the social preview image, from sot's logo
│   └── assets.ts          Tailwind (PostCSS), esbuild and Pagefind, run inside Eleventy
└── src/
    ├── _data/
    │   ├── nav.json       the file tree, status bar sections and page order
    │   ├── overview.json  the home page's intro, views and commands
    │   ├── site.json      title and description
    │   └── sot.json       generated from sot, not committed (see below)
    ├── _includes/         the window layout, the doc layout and their parts
    ├── assets/
    │   ├── css/main.css   themes and the terminal look
    │   └── ts/            palette, keyboard shortcuts, panes, theme switching
    ├── commands/          one page per command
    ├── *.md, index.njk    the other pages
    └── *.njk              llms.txt, the Markdown copies, sitemap.xml, robots.txt
```

- **A page** is Markdown with front matter: `title`, `description`, `window` (which status bar section it belongs to) and, for command pages, `cmds` (which `--help` outputs to show above it). Add it to `src/_data/nav.json` to put it in the tree.
- **Generated data**: `scripts/build_docs_data.py` reads the `--help` output of every command, the key bindings and the config template from sot into `src/_data/sot.json`. Run it again after changing a flag or a binding; CI always does.
- **Search** is [Pagefind](https://pagefind.app/), indexed after each build. Open it with `/` or `Ctrl+K`.
- **Themes**: light is Cappuccino, a warm reading palette (cream paper, espresso text, cinnamon and caramel), and dark is [Tokyo Night](https://github.com/folke/tokyonight.nvim). The site follows the system setting; `t` or the status bar switches, and the search palette has `theme system` to go back. The colours are CSS variables at the top of `main.css`, one `light-dark()` pair each.
- **For agents**: every page also exists as Markdown at its URL + `index.html.md` (`/commands/clean/index.html.md`), listed in `/llms.txt` ([llmstxt.org](https://llmstxt.org)) with all of them in `/llms-full.txt`. They're built from the same page sources, so a new shortcode needs a Markdown version in `config/llms.ts`; the build fails until it has one.
- **Search engines**: canonical URLs, Open Graph and Twitter cards, schema.org data (`SoftwareApplication` on the home page, `TechArticle` and breadcrumbs elsewhere), `sitemap.xml` and `robots.txt`. Crawlers only read `robots.txt` at a domain's root, so under `anistark.github.io/sot/` it only takes effect once the site has its own domain; until then, submit `sitemap.xml` in Google Search Console.
- **Icons and preview image**: `favicon.svg`, `favicon.ico`, `apple-touch-icon.png` and the 1200×630 `og.png` are drawn at build time from sot's logo in the Tokyo Night palette, with sharp. The preview's text is Roboto Mono turned into paths with fontkit, so it renders the same on any machine.
- **Fonts**: Roboto Mono, served with the site. It has no box-drawing or block glyphs, so the file tree is drawn with CSS borders and sot's logo is drawn as SVG from the same characters the app prints.
- **Base path**: the site lives under `/sot/` on GitHub Pages. CI takes the path and URL from the repository's Pages settings, so a custom domain needs no change here; locally, set `PATH_PREFIX=/` and `SITE_URL` to try one.
