import { expect, test, type Page } from "@playwright/test";

const API = "http://localhost:8000";

const FAKE_USER = {
  id: "u_1",
  name: "Ada Lovelace",
  email: "ada@example.com",
  role: "developer" as const,
  created_at: "2026-04-29T00:00:00+00:00",
};

/**
 * Mock the FastAPI auth endpoints. Stateful: tracks whether the user is "logged in"
 * so /auth/me reflects the current state across calls within a single test.
 */
async function mockAuth(
  page: Page,
  initial: { authenticated: boolean } = { authenticated: false },
) {
  let authed = initial.authenticated;

  await page.route(`${API}/auth/me`, (route) =>
    authed
      ? route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(FAKE_USER) })
      : route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "not authenticated" }) }),
  );

  await page.route(`${API}/auth/login`, (route) => {
    authed = true;
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(FAKE_USER),
    });
  });

  await page.route(`${API}/auth/register`, (route) => {
    authed = true;
    return route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify(FAKE_USER),
    });
  });

  await page.route(`${API}/auth/logout`, (route) => {
    authed = false;
    return route.fulfill({ status: 204, body: "" });
  });
}

test("unauthenticated user visiting /dashboard is redirected to /login", async ({ page }) => {
  await mockAuth(page);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login$/);
});

test("login flow lands on /dashboard and shows the user", async ({ page }) => {
  await mockAuth(page);
  await page.goto("/login");

  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password").fill("correcthorse");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("ada@example.com")).toBeVisible();
});

test("register flow lands on /dashboard", async ({ page }) => {
  await mockAuth(page);
  await page.goto("/register");

  await page.getByLabel("Name").fill("Ada Lovelace");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password").fill("correcthorse");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
});

test("logout returns user to /login", async ({ page }) => {
  await mockAuth(page, { authenticated: true });
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("login error from API surfaces inline", async ({ page }) => {
  await page.route(`${API}/auth/me`, (route) =>
    route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "not authenticated" }) }),
  );
  await page.route(`${API}/auth/login`, (route) =>
    route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "invalid credentials" }) }),
  );

  await page.goto("/login");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByText("invalid credentials")).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
});
