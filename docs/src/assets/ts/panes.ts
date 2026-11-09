/**
 * The tmux-style window: which pane is active, the scroll position in the
 * main pane's bottom border, the outline that follows the page, the tree
 * drawer on small screens and the copy buttons on code examples.
 */

const content = () => document.getElementById("content") as HTMLElement;

/** The element that scrolls the page: the main pane on wide screens, the document otherwise. */
export function scroller(): HTMLElement {
  const body = content();
  return getComputedStyle(body).overflowY === "auto" ? body : (document.scrollingElement as HTMLElement);
}

export function scrollPage(by: number | "top" | "bottom"): void {
  const el = scroller();
  if (by === "top") el.scrollTo({ top: 0 });
  else if (by === "bottom") el.scrollTo({ top: el.scrollHeight });
  else el.scrollBy({ top: by });
}

function trackActivePane(): void {
  const panes = [...document.querySelectorAll<HTMLElement>(".panes > .pane")];
  const activate = (pane: HTMLElement | null) => {
    if (!pane) return;
    for (const p of panes) p.classList.toggle("is-active", p === pane);
  };
  for (const pane of panes) {
    pane.addEventListener("pointerdown", () => activate(pane));
    pane.addEventListener("focusin", () => activate(pane));
  }
}

/** Vim's ruler: Top, Bot, All or a percentage. */
function trackScrollPosition(): void {
  const label = document.getElementById("scroll-pos");
  const body = content();
  if (!label) return;
  const update = () => {
    const max = body.scrollHeight - body.clientHeight;
    if (max <= 0) label.textContent = "all";
    else if (body.scrollTop <= 0) label.textContent = "top";
    else if (body.scrollTop >= max - 1) label.textContent = "bot";
    else label.textContent = `${Math.round((body.scrollTop / max) * 100)}%`;
  };
  body.addEventListener("scroll", () => requestAnimationFrame(update), { passive: true });
  window.addEventListener("resize", update);
  update();
}

/** Highlight the outline entry for the section being read. */
function trackOutline(): void {
  const links = [...document.querySelectorAll<HTMLAnchorElement>(".toc a")];
  if (!links.length) return;
  const headings = links
    .map((a) => document.getElementById(decodeURIComponent(a.hash.slice(1))))
    .filter((h): h is HTMLElement => h !== null);

  let frame = 0;
  const update = () => {
    frame = 0;
    const el = scroller();
    const top = el === content() ? el.getBoundingClientRect().top : 0;
    let current = 0;
    headings.forEach((h, i) => {
      if (h.getBoundingClientRect().top - top < 120) current = i;
    });
    // At the very bottom the last sections can't scroll up to the top; mark the last one.
    if (el.scrollTop > 0 && el.scrollTop + el.clientHeight >= el.scrollHeight - 2) current = headings.length - 1;
    links.forEach((a, i) => a.classList.toggle("is-current", i === current));
  };
  const schedule = () => {
    if (!frame) frame = requestAnimationFrame(update);
  };
  content().addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("scroll", schedule, { passive: true });
  update();
}

function treeDrawer(): void {
  const toggle = document.getElementById("tree-toggle");
  const tree = document.getElementById("tree");
  if (!toggle || !tree) return;
  const set = (open: boolean) => {
    tree.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
  };
  toggle.addEventListener("click", () => set(!tree.classList.contains("is-open")));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") set(false);
  });
  document.addEventListener("click", (e) => {
    const target = e.target as Node;
    if (!tree.contains(target) && !toggle.contains(target)) set(false);
  });
}

function copyButtons(): void {
  for (const button of document.querySelectorAll<HTMLButtonElement>(".term-block .copy")) {
    button.hidden = false;
    button.addEventListener("click", async () => {
      const code = button.closest(".term-block")?.querySelector("code");
      if (!code) return;
      try {
        await navigator.clipboard.writeText(code.innerText.trimEnd());
        button.textContent = "copied";
        button.classList.add("done");
      } catch {
        button.textContent = "press ctrl+c";
      }
      setTimeout(() => {
        button.textContent = "copy";
        button.classList.remove("done");
      }, 1600);
    });
  }
}

export function initPanes(): void {
  trackActivePane();
  trackScrollPosition();
  trackOutline();
  treeDrawer();
  copyButtons();
  // On narrow screens the status bar scrolls; keep the current section in view.
  const windows = document.querySelector<HTMLElement>(".statusbar .windows");
  const current = windows?.querySelector<HTMLElement>("[aria-current]");
  if (windows && current && current.offsetLeft + current.offsetWidth > windows.clientWidth) {
    windows.scrollLeft = current.offsetLeft - 8;
  }
}
