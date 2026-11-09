import { initKeys } from "./keys.ts";
import { initPalette } from "./palette.ts";
import { initPanes } from "./panes.ts";
import { initTheme } from "./theme.ts";
import type { NavEntry, NavItem } from "./types.ts";

const base = document.documentElement.dataset.base ?? "/";

function pages(): NavItem[] {
  try {
    const tree = JSON.parse(document.getElementById("nav-data")?.textContent ?? "[]") as NavEntry[];
    return tree.flatMap((entry) => ("dir" in entry ? entry.children : [entry]));
  } catch {
    return [];
  }
}

function initDialogs(openPalette: () => void): () => void {
  const keys = document.getElementById("keys") as HTMLDialogElement | null;
  const openKeys = () => keys?.showModal();
  keys?.addEventListener("click", (e) => {
    if (e.target === keys) keys.close();
  });
  for (const button of document.querySelectorAll<HTMLElement>("[data-open]")) {
    button.addEventListener("click", () => (button.dataset.open === "keys" ? openKeys() : openPalette()));
  }
  return openKeys;
}

initTheme();
initPanes();
const palette = initPalette(base, pages());
const openKeys = initDialogs(() => palette.open());
initKeys({ openPalette: () => palette.open(), openKeys });
