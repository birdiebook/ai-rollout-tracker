// Types shared by the layout's head tags, the citation line and describe.server.ts (W12).

export interface Citation {
  /** what is cited: 'serie "<label>" (<key>; källa: <source>)' or the page title */
  what: string;
  /** "version per" date (the bundle's build day; for a series the day its levels were read) */
  date: string;
  /** short commit of the build, null for fixtures */
  commit: string | null;
}

export interface PageMeta {
  title: string;
  description: string;
  /** the page sets its own <meta name="description"> (the layout then leaves it out) */
  ownDescription: boolean;
  /** share image path below <base>/og/, without extension */
  og: string;
  imageAlt: string;
  cite: Citation;
}
