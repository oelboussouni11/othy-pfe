import { expect, test, type Page } from "@playwright/test";

const API = "http://localhost:8000";

const USER = {
  id: "u_1",
  name: "Ada Lovelace",
  email: "ada@example.com",
  role: "developer",
  created_at: "2026-04-29T00:00:00+00:00",
};

const SAMPLE_PROJECT = {
  id: "p_1",
  name: "Acme Site",
  client_name: "Acme Inc",
  production_url: "https://acme.com",
  staging_url: "https://staging.acme.com",
  status: "draft",
  owner_id: "u_1",
  created_at: "2026-04-29T00:00:00+00:00",
};

/** Stateful in-memory project store for the duration of one test. */
async function mockApi(page: Page, initial: typeof SAMPLE_PROJECT[] = []) {
  const projects = new Map<string, typeof SAMPLE_PROJECT>();
  for (const p of initial) projects.set(p.id, { ...p });

  await page.route(`${API}/auth/me`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(USER),
    }),
  );

  await page.route(`${API}/projects`, async (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([...projects.values()]),
      });
    }
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON();
      const created = {
        ...SAMPLE_PROJECT,
        ...body,
        id: `p_${projects.size + 1}`,
        owner_id: USER.id,
        created_at: new Date().toISOString(),
      };
      projects.set(created.id, created);
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(created),
      });
    }
    return route.continue();
  });

  await page.route(new RegExp(`${API}/projects/[^/]+$`), async (route) => {
    const url = new URL(route.request().url());
    const id = url.pathname.split("/").pop()!;
    const project = projects.get(id);
    const method = route.request().method();

    if (!project) {
      return route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "project not found" }),
      });
    }

    if (method === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(project),
      });
    }
    if (method === "PATCH") {
      Object.assign(project, route.request().postDataJSON());
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(project),
      });
    }
    if (method === "DELETE") {
      projects.delete(id);
      return route.fulfill({ status: 204, body: "" });
    }
    return route.continue();
  });
}

test("empty state renders with create CTA", async ({ page }) => {
  await mockApi(page);
  await page.goto("/projects");

  await expect(page.getByRole("heading", { name: "No projects yet" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Create your first project" })).toBeVisible();
});

test("list renders projects when API returns them", async ({ page }) => {
  await mockApi(page, [SAMPLE_PROJECT]);
  await page.goto("/projects");

  await expect(page.getByText("Acme Site")).toBeVisible();
  await expect(page.getByText("Acme Inc")).toBeVisible();
  await expect(page.getByText("https://acme.com")).toBeVisible();
});

test("create project flow lands on detail page", async ({ page }) => {
  await mockApi(page);
  await page.goto("/projects/new");

  await page.getByLabel("Project name").fill("New Co");
  await page.getByLabel("Client (optional)").fill("New Co Inc");
  await page.getByLabel("Production URL").fill("https://newco.com");
  await page.getByLabel("Staging URL (optional)").fill("https://staging.newco.com");
  await page.getByRole("button", { name: "Create project" }).click();

  await expect(page).toHaveURL(/\/projects\/p_\d+$/);
  await expect(page.getByRole("heading", { name: "New Co" })).toBeVisible();
});

test("edit project updates the detail view", async ({ page }) => {
  await mockApi(page, [SAMPLE_PROJECT]);
  await page.goto("/projects/p_1");

  await page.getByRole("button", { name: "Edit" }).click();
  await page.getByLabel("Project name").fill("Acme Renamed");
  await page.getByRole("button", { name: "Save changes" }).click();

  await expect(page.getByRole("heading", { name: "Acme Renamed" })).toBeVisible();
});

test("delete project returns to list", async ({ page }) => {
  await mockApi(page, [SAMPLE_PROJECT]);
  await page.goto("/projects/p_1");

  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "Delete" }).click();

  await expect(page).toHaveURL(/\/projects$/);
  await expect(page.getByRole("heading", { name: "No projects yet" })).toBeVisible();
});
