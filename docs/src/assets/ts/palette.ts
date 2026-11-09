/**
 * The command palette (`/`, Ctrl+K, ⌘K): jump to a page, search every page
 * with Pagefind, or switch theme. Works like sot's own Ctrl+P palette.
 */
import { type ThemeChoice, setTheme } from "./theme.ts";
import type { NavItem, Pagefind } from "./types.ts";

interface Item {
  group: "pages" | "search" | "theme";
  label: string;
  hint?: string;
  excerpt?: string;
  url?: string;
  run?: () => void;
}

const MAX_RESULTS = 8;

export interface Palette {
  open(query?: string): void;
}

export function initPalette(base: string, pages: NavItem[]): Palette {
  const dialog = document.getElementById("palette") as HTMLDialogElement;
  const input = document.getElementById("palette-input") as HTMLInputElement;
  const list = document.getElementById("palette-list") as HTMLUListElement;

  let items: Item[] = [];
  let selected = 0;
  let pagefind: Promise<Pagefind | null> | undefined;
  let query = "";

  const loadPagefind = () => {
    pagefind ??= import(/* @vite-ignore */ `${base}pagefind/pagefind.js`)
      .then(async (pf: Pagefind) => {
        await pf.options({ baseUrl: base, excerptLength: 18 });
        await pf.init();
        return pf;
      })
      .catch(() => null);
    return pagefind;
  };

  const pageItems = (q: string): Item[] =>
    pages
      .map((p) => ({ page: p, command: p.command ?? `cat ${p.title}.md` }))
      .filter(({ page, command }) => !q || `${page.title} ${command}`.toLowerCase().includes(q))
      .map(({ page, command }) => ({ group: "pages", label: command, hint: page.url, url: page.url }));

  const THEME_ITEMS: { choice: ThemeChoice; hint: string }[] = [
    { choice: "dark", hint: "Tokyo Night" },
    { choice: "light", hint: "Cappuccino" },
    { choice: "system", hint: "follow your system" },
  ];
  const themeItems = (q: string): Item[] =>
    THEME_ITEMS.filter(({ choice, hint }) => !q || `theme ${choice} ${hint}`.toLowerCase().includes(q)).map(({ choice, hint }) => ({
      group: "theme",
      label: `theme ${choice}`,
      hint,
      run: () => setTheme(choice),
    }));

  const render = () => {
    list.replaceChildren();
    if (!items.length) {
      const empty = document.createElement("li");
      empty.className = "px-[2ch] py-2 text-muted";
      empty.textContent = query ? `zsh: no matches found: ${query}` : "";
      list.append(empty);
      return;
    }
    let group = "";
    items.forEach((item, i) => {
      if (item.group !== group) {
        group = item.group;
        const heading = document.createElement("li");
        heading.setAttribute("role", "presentation");
        heading.className = "px-[2ch] pt-2 pb-1 text-xs text-faint";
        heading.textContent = `# ${group}`;
        list.append(heading);
      }
      const li = document.createElement("li");
      li.id = `palette-item-${i}`;
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", String(i === selected));
      li.className = "cursor-pointer px-[2ch] py-1.5";

      const row = document.createElement("div");
      row.className = "flex items-baseline justify-between gap-4";
      const label = document.createElement("span");
      label.className = "label truncate text-strong";
      label.textContent = item.label;
      row.append(label);
      if (item.hint) {
        const hint = document.createElement("span");
        hint.className = "shrink-0 text-xs text-faint";
        hint.textContent = item.hint;
        row.append(hint);
      }
      li.append(row);

      if (item.excerpt) {
        const excerpt = document.createElement("div");
        excerpt.className = "mt-0.5 line-clamp-2 text-xs text-muted";
        // Pagefind escapes page text and only adds <mark> around matches.
        excerpt.innerHTML = item.excerpt;
        li.append(excerpt);
      }

      li.addEventListener("pointermove", () => select(i));
      li.addEventListener("click", () => activate(item));
      list.append(li);
    });
    input.setAttribute("aria-activedescendant", `palette-item-${selected}`);
  };

  const select = (i: number) => {
    if (i === selected || !items.length) return;
    selected = (i + items.length) % items.length;
    for (const li of list.querySelectorAll('[role="option"]')) {
      li.setAttribute("aria-selected", String(li.id === `palette-item-${selected}`));
    }
    input.setAttribute("aria-activedescendant", `palette-item-${selected}`);
    list.querySelector(`#palette-item-${selected}`)?.scrollIntoView({ block: "nearest" });
  };

  const activate = (item: Item | undefined) => {
    if (!item) return;
    dialog.close();
    if (item.run) item.run();
    else if (item.url) location.href = item.url.startsWith(base) ? item.url : base + item.url.replace(/^\//, "");
  };

  const update = async () => {
    query = input.value.trim().toLowerCase();
    items = [...pageItems(query), ...themeItems(query)];
    selected = 0;
    render();
    if (query.length < 2) return;

    const pf = await loadPagefind();
    if (!pf) return;
    const search = await pf.debouncedSearch(query, {}, 120);
    if (!search || input.value.trim().toLowerCase() !== query) return;
    const results = await Promise.all(search.results.slice(0, MAX_RESULTS).map((r) => r.data()));
    const found: Item[] = results.map((r) => {
      const best = r.sub_results.find((s) => s.url.includes("#")) ?? r.sub_results[0];
      const title = r.meta.title ?? r.url;
      return {
        group: "search",
        label: best && best.title !== title ? `${title} › ${best.title}` : title,
        excerpt: best?.excerpt ?? r.excerpt,
        url: best?.url ?? r.url,
      };
    });
    if (input.value.trim().toLowerCase() !== query) return;
    items = [...found, ...items];
    render();
  };

  input.addEventListener("input", () => void update());
  input.addEventListener("keydown", (e) => {
    const down = e.key === "ArrowDown" || (e.ctrlKey && e.key === "n");
    const up = e.key === "ArrowUp" || (e.ctrlKey && e.key === "p");
    if (down || up) {
      e.preventDefault();
      select(selected + (down ? 1 : -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      activate(items[selected]);
    }
  });
  // A click on the backdrop closes it.
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });

  return {
    open(initial = "") {
      if (dialog.open) return;
      dialog.showModal();
      input.value = initial;
      void update();
      input.focus();
      void loadPagefind();
    },
  };
}
