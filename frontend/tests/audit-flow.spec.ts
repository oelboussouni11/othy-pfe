import { expect, test, type Page } from "@playwright/test";

const API = "http://localhost:8000";

const USER = {
  id: "u_1",
  name: "Ada",
  email: "ada@example.com",
  role: "developer",
  created_at: "2026-04-29T00:00:00+00:00",
};

const PROJECT = {
  id: "p_1",
  name: "Acme Site",
  client_name: "Acme Inc",
  production_url: "https://acme.com",
  staging_url: "https://staging.acme.com",
  status: "draft",
  owner_id: "u_1",
  created_at: "2026-04-29T00:00:00+00:00",
};

const COMPLETED_AUDIT = {
  id: "a_prod",
  project_id: "p_1",
  environment: "production",
  status: "completed",
  pages_crawled: 12,
  broken_links_count: 1,
  seo_score: 84,
  error_message: null,
  started_at: "2026-04-29T00:01:00+00:00",
  finished_at: "2026-04-29T00:02:00+00:00",
  created_at: "2026-04-29T00:01:00+00:00",
  companion_audit_id: "a_stg",
  verdict: "no_go",
  issues: [
    {
      id: "i_1",
      page_url: "https://acme.com/missing",
      type: "client_error",
      severity: "critical",
      message: "https://acme.com/missing: status 404",
      recommendation: "Update or remove the link.",
      status_code: 404,
    },
    {
      id: "i_2",
      page_url: "https://acme.com/",
      type: "title_too_short",
      severity: "warning",
      message: "<title> is 8 chars (min 30)",
      recommendation: "Expand the title.",
      status_code: null,
    },
  ],
};

const DIFF = {
  audit_id: "a_prod",
  companion_audit_id: "a_stg",
  pair_complete: true,
  verdict: "no_go",
  diffs: [
    {
      id: "d_1",
      page_url: "/api",
      field: "status_code",
      staging_value: "200",
      production_value: "500",
      change_type: "modified",
      severity: "critical",
    },
  ],
};

async function mockApi(page: Page, opts: { existingAudits?: object[] } = {}) {
  await page.route(`${API}/auth/me`, (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(USER) }),
  );
  await page.route(`${API}/projects/p_1`, (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(PROJECT) }),
  );

  let audits = opts.existingAudits ?? [];

  await page.route(`${API}/projects/p_1/audits`, async (r) => {
    if (r.request().method() === "GET") {
      return r.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(audits),
      });
    }
    if (r.request().method() === "POST") {
      audits = [COMPLETED_AUDIT, ...audits];
      return r.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify([COMPLETED_AUDIT]),
      });
    }
    return r.continue();
  });

  await page.route(`${API}/audits/a_prod`, (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(COMPLETED_AUDIT),
    }),
  );

  await page.route(`${API}/audits/a_prod/diff`, (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(DIFF),
    }),
  );
}

test("project detail shows Run audit button and triggers a run", async ({ page }) => {
  await mockApi(page);
  await page.goto("/projects/p_1");

  await expect(page.getByRole("heading", { name: "Acme Site" })).toBeVisible();
  await expect(page.getByText("No audits yet")).toBeVisible();

  await page.getByRole("button", { name: "Run audit" }).click();

  // Both header and row show verdict — scope to the table.
  const table = page.getByRole("table");
  await expect(table.getByText("Completed")).toBeVisible();
  await expect(table.getByText("No-Go")).toBeVisible();
});

test("audit detail shows summary, issues, diff, and pages tabs", async ({ page }) => {
  await mockApi(page, { existingAudits: [COMPLETED_AUDIT] });
  await page.goto("/projects/p_1/audits/a_prod");

  // Summary
  await expect(page.getByText("Pages crawled")).toBeVisible();
  await expect(page.getByText("12", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("84").first()).toBeVisible();

  // Issues tab is default. The type filter dropdown also contains these strings,
  // so we scope to the issues list itself.
  const list = page.getByRole("list");
  await expect(list.getByText("client_error")).toBeVisible();
  await expect(list.getByText("title_too_short")).toBeVisible();

  // Filter to critical — title_too_short (warning) should disappear from list
  await page.getByLabel("Severity").selectOption("critical");
  await expect(list.getByText("client_error")).toBeVisible();
  await expect(list.getByText("title_too_short")).toHaveCount(0);

  // Diff tab
  await page.getByRole("button", { name: "Diff" }).click();
  await expect(page.getByText("status_code")).toBeVisible();
  await expect(page.getByText("500", { exact: true })).toBeVisible();

  // Pages tab — InsightsPanel also lists example URLs, so scope to the Pages table.
  await page.getByRole("button", { name: "Pages" }).click();
  await expect(
    page.getByRole("table").getByText("https://acme.com/missing"),
  ).toBeVisible();
});

test("audit detail polls while audit is running", async ({ page }) => {
  await page.route(`${API}/auth/me`, (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(USER) }),
  );

  // Time-based flip — first ~3s returns "running", then "completed". Survives
  // React's double-effect in dev mode without making the test count-sensitive.
  const start = Date.now();
  await page.route(`${API}/audits/a_prod`, (r) => {
    const status = Date.now() - start < 3000 ? "running" : "completed";
    return r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...COMPLETED_AUDIT,
        status,
        verdict: status === "completed" ? "no_go" : null,
      }),
    });
  });

  await page.goto("/projects/p_1/audits/a_prod");

  await expect(page.getByText("Running")).toBeVisible();
  await expect(page.getByText("Completed")).toBeVisible({ timeout: 10000 });
});
