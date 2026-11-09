/** Structured data (schema.org JSON-LD) for search engines. */
import { siteData, sotData } from "./data.ts";
import { absoluteUrl, plainText } from "./llms.ts";

interface PageInfo {
  url: string;
  title: string;
  description?: string;
}

export function structuredData(page: PageInfo, siteUrl: string): string {
  const site = siteData();
  const sot = sotData();
  const url = absoluteUrl(siteUrl, page.url);
  const website = { "@type": "WebSite", "@id": `${siteUrl}#website`, name: "sot docs", url: siteUrl, inLanguage: "en" };

  const graph: object[] = [website];
  if (page.url === "/") {
    graph.push({
      "@type": "SoftwareApplication",
      name: "sot",
      alternateName: "System Observation Tool",
      description: site.description,
      url: siteUrl,
      applicationCategory: "DeveloperApplication",
      applicationSubCategory: "System monitor",
      operatingSystem: "macOS, Linux, Windows",
      ...(sot && { softwareVersion: sot.version }),
      softwareRequirements: "Python 3.10 or newer",
      license: "https://opensource.org/licenses/MIT",
      downloadUrl: "https://pypi.org/project/sot/",
      installUrl: `${siteUrl}install/`,
      releaseNotes: `${siteUrl}changelog/`,
      screenshot: `${siteUrl}assets/img/demo.gif`,
      image: `${siteUrl}og.png`,
      author: { "@type": "Person", name: "Kumar Anirudha" },
      sameAs: [site.repo, "https://pypi.org/project/sot/"],
      offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
    });
  } else {
    const crumbs = [{ name: "sot", url: siteUrl }];
    if (page.url.startsWith("/commands/") && page.url !== "/commands/") crumbs.push({ name: "Commands", url: `${siteUrl}commands/` });
    crumbs.push({ name: page.title, url });
    graph.push(
      {
        "@type": "TechArticle",
        headline: page.title,
        description: plainText(page.description),
        url,
        inLanguage: "en",
        isPartOf: { "@id": `${siteUrl}#website` },
        about: { "@type": "SoftwareApplication", name: "sot", url: siteUrl },
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: crumbs.map((c, i) => ({ "@type": "ListItem", position: i + 1, name: c.name, item: c.url })),
      },
    );
  }

  // `<` is escaped so page text can never close the script tag.
  const json = JSON.stringify({ "@context": "https://schema.org", "@graph": graph }).replaceAll("<", "\\u003c");
  return `<script type="application/ld+json">${json}</script>`;
}
