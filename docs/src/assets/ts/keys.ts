/** Keyboard shortcuts, borrowed from sot where they make sense. */
import { scrollPage, scroller } from "./panes.ts";
import { toggleTheme } from "./theme.ts";

export interface KeyActions {
  openPalette(): void;
  openKeys(): void;
}

const LINE = 56;

function follow(rel: "prev" | "next"): void {
  const link = document.querySelector<HTMLAnchorElement>(`a[rel="${rel}"]`);
  if (link) location.href = link.href;
}

export function initKeys(actions: KeyActions): void {
  document.addEventListener("keydown", (e) => {
    if (e.defaultPrevented || e.isComposing) return;

    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      actions.openPalette();
      return;
    }

    const target = e.target as HTMLElement;
    if (target.closest("input, textarea, select, [contenteditable]") || document.querySelector("dialog[open]")) return;
    if (e.metaKey || e.altKey) return;

    if (e.ctrlKey) {
      const half = scroller().clientHeight / 2;
      if (e.key === "d") scrollPage(half);
      else if (e.key === "u") scrollPage(-half);
      else return;
      e.preventDefault();
      return;
    }

    switch (e.key) {
      case "/":
        e.preventDefault();
        actions.openPalette();
        break;
      case "?":
        actions.openKeys();
        break;
      case "j":
        scrollPage(LINE);
        break;
      case "k":
        scrollPage(-LINE);
        break;
      case "g":
        scrollPage("top");
        break;
      case "G":
        scrollPage("bottom");
        break;
      case "[":
        follow("prev");
        break;
      case "]":
        follow("next");
        break;
      case "t":
        toggleTheme();
        break;
      default:
        if (/^[1-9]$/.test(e.key)) {
          const link = document.querySelector<HTMLAnchorElement>(`[data-window="${e.key}"]`);
          if (link) location.href = link.href;
        }
    }
  });
}
