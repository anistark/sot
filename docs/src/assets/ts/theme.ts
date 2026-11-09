/**
 * Light (Cappuccino) or dark (Tokyo Night). The page follows the system
 * setting until you pick one; "system" goes back to following it.
 */
export type Theme = "light" | "dark";
export type ThemeChoice = Theme | "system";

const STORAGE_KEY = "sot-docs-theme";
const darkQuery = matchMedia("(prefers-color-scheme: dark)");

/** The theme on screen right now. */
export function currentTheme(): Theme {
  const chosen = document.documentElement.dataset.theme;
  if (chosen === "light" || chosen === "dark") return chosen;
  return darkQuery.matches ? "dark" : "light";
}

export function setTheme(choice: ThemeChoice): void {
  const root = document.documentElement;
  try {
    if (choice === "system") localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, choice);
  } catch {
    // Private mode or blocked storage: the choice just isn't remembered.
  }
  if (choice === "system") delete root.dataset.theme;
  else root.dataset.theme = choice;
  showThemeName();
}

export function toggleTheme(): void {
  setTheme(currentTheme() === "dark" ? "light" : "dark");
}

function showThemeName(): void {
  for (const label of document.querySelectorAll<HTMLElement>("[data-theme-name]")) {
    label.textContent = currentTheme();
  }
}

export function initTheme(): void {
  showThemeName();
  darkQuery.addEventListener("change", showThemeName);
  for (const button of document.querySelectorAll<HTMLElement>("[data-theme-toggle]")) {
    button.addEventListener("click", toggleTheme);
  }
}
