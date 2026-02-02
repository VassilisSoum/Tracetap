import { test, expect } from '@playwright/test';

test.describe('TodoMVC - Comprehensive Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('https://demo.playwright.dev/todomvc/');
    // Verify initial state
    await expect(page.locator('.todo-list li')).toHaveCount(0);
  });

  test('add todo with validation', async ({ page }) => {
    const newTodoInput = page.locator('input.new-todo');

    // Action: Fill and submit
    await newTodoInput.fill('Buy groceries');
    expect(await newTodoInput.inputValue()).toBe('Buy groceries');

    await newTodoInput.press('Enter');

    // Verify API response
    const response = await page.waitForResponse(/\/api\/todos/);
    expect(response.status()).toBe(201);

    const body = await response.json();
    expect(body).toHaveProperty('id');
    expect(body).toHaveProperty('text', 'Buy groceries');
    expect(body).toHaveProperty('completed', false);
    expect(body).toHaveProperty('createdAt');

    // Verify UI updated
    await expect(page.locator('.todo-list li')).toHaveCount(1);
    await expect(page.locator('text=Buy groceries')).toBeVisible();

    // Verify input cleared
    await expect(newTodoInput).toHaveValue('');
  });

  test('add multiple todos with schema validation', async ({ page }) => {
    const newTodoInput = page.locator('input.new-todo');
    const todos = ['Buy groceries', 'Walk the dog', 'Write documentation'];

    for (const todoText of todos) {
      await newTodoInput.fill(todoText);
      await newTodoInput.press('Enter');

      const response = await page.waitForResponse(/\/api\/todos/);
      expect(response.status()).toBe(201);

      const body = await response.json();
      expect(body.text).toBe(todoText);
      expect(body.completed).toBe(false);
      expect(typeof body.id).toBe('number');
    }

    // Verify all todos appear
    const todoItems = await page.locator('.todo-list li').count();
    expect(todoItems).toBe(3);
  });

  test('toggle todo completion status', async ({ page }) => {
    // Setup: Add a todo
    const newTodoInput = page.locator('input.new-todo');
    await newTodoInput.fill('Buy groceries');
    await newTodoInput.press('Enter');

    const createResponse = await page.waitForResponse(/\/api\/todos/);
    const createdTodo = await createResponse.json();
    const todoId = createdTodo.id;

    // Action: Toggle completion
    const checkbox = page.locator('input.toggle').first();
    await checkbox.click();

    // Verify API response
    const updateResponse = await page.waitForResponse(`/api/todos/${todoId}`);
    expect(updateResponse.request().method()).toBe('PATCH');
    expect(updateResponse.status()).toBe(200);

    const updatedTodo = await updateResponse.json();
    expect(updatedTodo.completed).toBe(true);
    expect(updatedTodo.id).toBe(todoId);

    // Verify UI updated
    const todoItem = page.locator('.todo-list li').first();
    await expect(todoItem).toHaveClass(/completed/);
  });

  test('filter todos by status', async ({ page }) => {
    // Setup: Add todos and mark some complete
    const newTodoInput = page.locator('input.new-todo');

    await newTodoInput.fill('Buy groceries');
    await newTodoInput.press('Enter');
    await page.waitForResponse(/\/api\/todos/);

    await newTodoInput.fill('Walk the dog');
    await newTodoInput.press('Enter');
    await page.waitForResponse(/\/api\/todos/);

    // Mark first as complete
    await page.locator('input.toggle').first().click();
    await page.waitForResponse(/\/api\/todos\/\d+/);

    // Action: Filter by active
    await page.click('.filters a[href="#/active"]');

    // Verify only active todos shown
    const visibleItems = await page.locator('.todo-list li:visible').count();
    expect(visibleItems).toBe(1);
    await expect(page.locator('text=Walk the dog')).toBeVisible();
    await expect(page.locator('text=Buy groceries')).not.toBeVisible();

    // Action: Filter by completed
    await page.click('.filters a[href="#/completed"]');

    // Verify only completed todos shown
    const completedItems = await page.locator('.todo-list li:visible').count();
    expect(completedItems).toBe(1);
    await expect(page.locator('text=Buy groceries')).toBeVisible();
    await expect(page.locator('text=Walk the dog')).not.toBeVisible();

    // Action: Show all
    await page.click('.filters a[href="#/"]');

    // Verify both shown
    const allItems = await page.locator('.todo-list li:visible').count();
    expect(allItems).toBe(2);
  });

  test('clear completed todos', async ({ page }) => {
    const newTodoInput = page.locator('input.new-todo');

    // Setup: Add multiple todos
    for (const todo of ['Task 1', 'Task 2', 'Task 3']) {
      await newTodoInput.fill(todo);
      await newTodoInput.press('Enter');
      await page.waitForResponse(/\/api\/todos/);
    }

    // Mark some as complete
    await page.locator('input.toggle').first().click();
    await page.waitForResponse(/\/api\/todos\/\d+/);

    await page.locator('input.toggle').nth(1).click();
    await page.waitForResponse(/\/api\/todos\/\d+/);

    // Action: Clear completed
    const clearButton = page.locator('button:has-text("Clear completed")');
    if (await clearButton.isVisible()) {
      await clearButton.click();
      await page.waitForResponse(/\/api\/todos\//);
    }

    // Verify only active todos remain
    const remainingItems = await page.locator('.todo-list li').count();
    expect(remainingItems).toBeLessThanOrEqual(1);
  });

  test('handle empty todo input gracefully', async ({ page }) => {
    const newTodoInput = page.locator('input.new-todo');

    // Try to submit empty
    await newTodoInput.press('Enter');

    // Should not make API call for empty input
    let responseCaught = false;
    try {
      await page.waitForResponse(/\/api\/todos/, { timeout: 1000 });
      responseCaught = true;
    } catch (e) {
      // Expected: no response for empty input
    }

    expect(responseCaught).toBe(false);
    await expect(page.locator('.todo-list li')).toHaveCount(0);
  });

  test('verify todo count display', async ({ page }) => {
    const newTodoInput = page.locator('input.new-todo');

    // Add 3 todos
    for (let i = 1; i <= 3; i++) {
      await newTodoInput.fill(`Task ${i}`);
      await newTodoInput.press('Enter');
      await page.waitForResponse(/\/api\/todos/);
    }

    // Check count
    const counter = page.locator('.todo-count');
    const countText = await counter.textContent();
    expect(countText).toContain('3');
  });
});
