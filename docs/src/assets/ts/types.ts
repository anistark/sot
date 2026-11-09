/** A page in the docs tree (see src/_data/nav.json). */
export interface NavItem {
  title: string;
  url: string;
  command?: string;
}

export interface NavDir {
  dir: string;
  children: NavItem[];
}

export type NavEntry = NavItem | NavDir;

/** The parts of Pagefind's browser API the palette uses. */
export interface PagefindSubResult {
  title: string;
  url: string;
  excerpt: string;
}

export interface PagefindResultData {
  url: string;
  excerpt: string;
  meta: { title?: string };
  sub_results: PagefindSubResult[];
}

export interface PagefindResult {
  id: string;
  data(): Promise<PagefindResultData>;
}

export interface Pagefind {
  options(options: { baseUrl?: string; excerptLength?: number }): Promise<void>;
  init(): Promise<void> | void;
  debouncedSearch(query: string, options?: object, timeout?: number): Promise<{ results: PagefindResult[] } | null>;
}
