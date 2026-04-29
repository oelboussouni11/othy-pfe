/**
 * Translates raw issue types from the audit engine into PM-friendly labels and
 * explanations. The `recommendation` text comes from each Issue (set by the
 * engine), but the *why it matters* lives here.
 */

import type { AuditIssue, Severity } from "@/lib/audits";

type TypeMeta = {
  label: string;
  why: string;
};

const TYPE_META: Record<string, TypeMeta> = {
  // ---------- title ----------
  missing_title: {
    label: "Missing <title> tag",
    why:
      "The <title> is the primary headline for search engines and the browser tab. Pages without it look broken and rank poorly.",
  },
  title_too_short: {
    label: "Title is too short",
    why:
      "Short titles miss keyword opportunities and look thin in search results. Aim for 30–65 characters.",
  },
  title_too_long: {
    label: "Title is too long",
    why:
      "Google truncates titles around 60 characters. Anything longer gets cut off in the search snippet.",
  },

  // ---------- meta description ----------
  missing_meta_description: {
    label: "Missing meta description",
    why:
      "Search results show this as the snippet under the page title. Without it, Google generates one — which often picks bad copy.",
  },
  meta_description_too_short: {
    label: "Meta description too short",
    why:
      "Short descriptions waste valuable real estate in the search snippet. 70–160 characters is the sweet spot.",
  },
  meta_description_too_long: {
    label: "Meta description too long",
    why:
      "Anything past ~160 characters gets truncated with an ellipsis in search results.",
  },

  // ---------- headings ----------
  missing_h1: {
    label: "No <h1> on the page",
    why:
      "The H1 tells crawlers and screen readers what the page is about. Skipping it weakens SEO and accessibility.",
  },
  multiple_h1: {
    label: "More than one <h1>",
    why:
      "Multiple H1s confuse the page hierarchy. There should be exactly one — the page's main heading.",
  },

  // ---------- canonical ----------
  missing_canonical: {
    label: "Missing canonical link",
    why:
      "Without a canonical, search engines may treat trailing-slash and query-string duplicates as separate pages, splitting your ranking signal.",
  },

  // ---------- open graph ----------
  missing_og_title: {
    label: "Missing Open Graph title",
    why:
      "When the page is shared on LinkedIn, Slack, X, or WhatsApp, the preview falls back to whatever scraper finds first — usually a worse headline.",
  },
  missing_og_description: {
    label: "Missing Open Graph description",
    why:
      "Without og:description, link previews on social platforms either look empty or pull random copy from the page.",
  },
  missing_og_image: {
    label: "Missing Open Graph image",
    why:
      "Without og:image, link previews show no thumbnail. Click-through rates on social drops noticeably.",
  },

  // ---------- accessibility ----------
  missing_alt_text: {
    label: "Images missing alt text",
    why:
      "Screen readers skip images without alt. It also hurts image search and is a common WCAG failure.",
  },

  // ---------- links ----------
  broken_link: {
    label: "Broken link (network failure)",
    why:
      "Visitors clicking this link hit nothing. Hurts conversion and trust. Often caused by typos or removed pages.",
  },
  client_error: {
    label: "Link returns 4xx",
    why:
      "The destination doesn't exist (404) or refuses access. Visitors see an error page instead of content.",
  },
  server_error: {
    label: "Link returns 5xx",
    why:
      "The destination server is failing. Could be temporary, but if it persists it's a bigger outage to fix.",
  },
  temporary_redirect: {
    label: "Link uses a temporary redirect (302)",
    why:
      "Temporary redirects don't pass full SEO signal. If the redirect is permanent, switch it to 301.",
  },
  permanent_redirect: {
    label: "Link goes through a 301 redirect",
    why:
      "Each redirect adds a hop and slightly slows the user. Update the link to point directly at the final URL.",
  },
  long_redirect_chain: {
    label: "Long redirect chain (>2 hops)",
    why:
      "Multi-hop redirects compound load time and lose ranking signal at each step. Collapse them.",
  },
};

const SEVERITY_RANK: Record<Severity, number> = {
  critical: 0,
  warning: 1,
  info: 2,
  ok: 3,
};

export type Insight = {
  type: string;
  label: string;
  why: string;
  recommendation: string;
  severity: Severity;
  count: number;
  example_pages: string[]; // up to 3 examples
};

export function summarizeIssues(issues: AuditIssue[]): Insight[] {
  const byType = new Map<string, Insight>();

  for (const issue of issues) {
    if (issue.severity === "ok") continue;
    const existing = byType.get(issue.type);
    if (existing) {
      existing.count++;
      if (existing.example_pages.length < 3 && !existing.example_pages.includes(issue.page_url)) {
        existing.example_pages.push(issue.page_url);
      }
    } else {
      const meta = TYPE_META[issue.type] ?? {
        label: issue.type.replace(/_/g, " "),
        why: "",
      };
      byType.set(issue.type, {
        type: issue.type,
        label: meta.label,
        why: meta.why,
        recommendation: issue.recommendation,
        severity: issue.severity,
        count: 1,
        example_pages: [issue.page_url],
      });
    }
  }

  return [...byType.values()].sort((a, b) => {
    if (SEVERITY_RANK[a.severity] !== SEVERITY_RANK[b.severity]) {
      return SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
    }
    return b.count - a.count;
  });
}
