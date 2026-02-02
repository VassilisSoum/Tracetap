import { test, expect } from '@playwright/test';

test.describe('TodoMVC - Basic Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('https://demo.playwright.dev/todomvc/');
  });

  test('add a todo', async ({ page }) => {
    await page.fill('input.new-todo', 'Buy groceries');
    await page.press('input.new-todo', 'Enter');

    const response = await page.waitForResponse(/\/api\/todos/);
    expect(response.status()).toBe(201);

    // Verify the todo appears in the list
    await expect(page.locator('text=Buy groceries')).toBeVisible();
  });

  test('add multiple todos', async ({ page }) => {
    await page.fill('input.new-todo', 'Buy groceries');
    await page.press('input.new-todo', 'Enter');

    const res1 = await page.waitForResponse(/\/api\/todos/);
    expect(res1.status()).toBe(201);

    await page.fill('input.new-todo', 'Walk the dog');
    await page.press('input.new-todo', 'Enter');

    const res2 = await page.waitForResponse(/\/api\/todos/);
    expect(res2.status()).toBe(201);

    const todoItems = await page.locator('.todo-list li').count();
    expect(todoItems).toBeGreaterThan(0);
  });

  test('toggle todo completion', async ({ page }) => {
    await page.fill('input.new-todo', 'Buy groceries');
    await page.press('input.new-todo', 'Enter');
    await page.waitForResponse(/\/api\/todos/);

    const checkbox = page.locator('input.toggle').first();
    await checkbox.click();

    const response = await page.waitForResponse(/\/api\/todos\/\d+/);
    expect(response.status()).toBe(200);

    const todo = await response.json();
    expect(todo.completed).toBe(true);
  });

  test('filter active todos', async ({ page }) => {
    await page.fill('input.new-todo', 'Buy groceries');
    await page.press('input.new-todo', 'Enter');
    await page.waitForResponse(/\/api\/todos/);

    await page.click('.filters a[href="#/active"]');
    await page.waitForNavigation();

    const todoItems = await page.locator('.todo-list li:not(.completed)').count();
    expect(todoItems).toBeGreaterThanOrEqual(1);
  });
});
