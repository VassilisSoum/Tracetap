import { test, expect } from '@playwright/test';
import { z } from 'zod';

// API Contract Schemas v1.0.0

const TodoSchema = z.object({
  id: z.number().positive('ID must be positive'),
  text: z.string().min(1, 'Todo text cannot be empty').max(500),
  completed: z.boolean().default(false),
  createdAt: z.string().datetime()
});

const TodoListSchema = z.array(TodoSchema);

const TodoCreateRequestSchema = z.object({
  text: z.string().min(1).max(500)
});

// Helper function to validate schema
async function validateSchema<T>(
  data: unknown,
  schema: z.ZodSchema<T>,
  testName: string
): Promise<{ success: boolean; errors?: z.ZodError }> {
  const result = schema.safeParse(data);
  if (!result.success) {
    console.error(`[${testName}] Schema validation failed:`, result.error.errors);
  }
  return result;
}

test.describe('TodoMVC - Regression Tests (API Contract)', () => {
  const baseURL = 'https://demo.playwright.dev/todomvc/';

  test.beforeEach(async ({ page }) => {
    await page.goto(baseURL);
  });

  test('POST /api/todos - create todo contract validation', async ({ page }) => {
    const newTodoInput = page.locator('input.new-todo');
    await newTodoInput.fill('Buy groceries');
    await newTodoInput.press('Enter');

    const response = await page.waitForResponse(/\/api\/todos/);
    expect(response.status()).toBe(201);

    const body = await response.json();

    // Validate against contract schema
    const validation = await validateSchema(
      body,
      TodoSchema,
      'POST /api/todos'
    );
    expect(validation.success).toBe(true);

    // Additional breaking change detection
    expect(body).toHaveProperty('id');
    expect(body).toHaveProperty('text');
    expect(body).toHaveProperty('completed');
    expect(body).toHaveProperty('createdAt');

    // Verify no unexpected fields (schema evolution check)
    const allowedFields = new Set(['id', 'text', 'completed', 'createdAt', 'updatedAt']);
    const unexpectedFields = Object.keys(body).filter(
      key => !allowedFields.has(key)
    );

    if (unexpectedFields.length > 0) {
      console.warn('⚠️ New fields detected in response:', unexpectedFields);
    }
  });

  test('PATCH /api/todos/:id - update todo contract validation', async ({ page }) => {
    // Setup: Create a todo first
    const newTodoInput = page.locator('input.new-todo');
    await newTodoInput.fill('Test todo');
    await newTodoInput.press('Enter');

    const createResponse = await page.waitForResponse(/\/api\/todos/);
    const createdTodo = await createResponse.json();
    const todoId = createdTodo.id;

    // Action: Toggle completion
    const checkbox = page.locator('input.toggle').first();
    await checkbox.click();

    const updateResponse = await page.waitForResponse(`/api/todos/${todoId}`);
    expect(updateResponse.status()).toBe(200);

    const updatedBody = await updateResponse.json();

    // Validate against contract schema
    const validation = await validateSchema(
      updatedBody,
      TodoSchema,
      `PATCH /api/todos/${todoId}`
    );
    expect(validation.success).toBe(true);

    // Breaking change detection
    expect(updatedBody.id).toBe(todoId);
    expect(typeof updatedBody.completed).toBe('boolean');
    expect(updatedBody.completed).toBe(true);
  });

  test('contract version check - detect schema violations', async ({ page }) => {
    const newTodoInput = page.locator('input.new-todo');
    await newTodoInput.fill('Regression test');
    await newTodoInput.press('Enter');

    const response = await page.waitForResponse(/\/api\/todos/);
    const body = await response.json();

    // Test schema evolution
    const requiredFields = ['id', 'text', 'completed', 'createdAt'];
    for (const field of requiredFields) {
      expect(body).toHaveProperty(field, `Missing required field: ${field}`);
    }

    // Test field types
    expect(typeof body.id).toBe('number');
    expect(typeof body.text).toBe('string');
    expect(typeof body.completed).toBe('boolean');
    expect(typeof body.createdAt).toBe('string');
  });

  test('detect breaking changes - required fields', async ({ page }) => {
    const newTodoInput = page.locator('input.new-todo');
    await newTodoInput.fill('Breaking change test');
    await newTodoInput.press('Enter');

    const response = await page.waitForResponse(/\/api\/todos/);
    const body = await response.json();

    // Ensure required fields are present
    const requiredFields = ['id', 'text', 'completed', 'createdAt'];
    const missingFields = requiredFields.filter(field => !(field in body));

    if (missingFields.length > 0) {
      throw new Error(
        `⚠️ BREAKING CHANGE: Missing required fields: ${missingFields.join(', ')}`
      );
    }

    // Ensure field types haven't changed
    if (typeof body.id !== 'number') {
      throw new Error('⚠️ BREAKING CHANGE: id type changed from number');
    }

    if (typeof body.completed !== 'boolean') {
      throw new Error('⚠️ BREAKING CHANGE: completed type changed from boolean');
    }
  });

  test('response time SLA - create todo', async ({ page }) => {
    const newTodoInput = page.locator('input.new-todo');
    await newTodoInput.fill('Performance test');

    const startTime = Date.now();
    await newTodoInput.press('Enter');

    const response = await page.waitForResponse(/\/api\/todos/);
    const endTime = Date.now();

    const responseTime = endTime - startTime;

    // SLA: Create should complete within 1000ms
    expect(responseTime).toBeLessThan(1000);

    console.log(`Create todo response time: ${responseTime}ms`);
  });

  test('response time SLA - update todo', async ({ page }) => {
    // Setup
    const newTodoInput = page.locator('input.new-todo');
    await newTodoInput.fill('SLA test');
    await newTodoInput.press('Enter');

    const createResponse = await page.waitForResponse(/\/api\/todos/);
    const todo = await createResponse.json();

    // Action: Update with timing
    const startTime = Date.now();
    await page.locator('input.toggle').first().click();

    const updateResponse = await page.waitForResponse(`/api/todos/${todo.id}`);
    const endTime = Date.now();

    const responseTime = endTime - startTime;

    // SLA: Update should complete within 500ms
    expect(responseTime).toBeLessThan(500);

    console.log(`Update todo response time: ${responseTime}ms`);
  });

  test('request format validation - POST body schema', async ({ page }) => {
    const newTodoInput = page.locator('input.new-todo');
    const testText = 'Request validation test';
    await newTodoInput.fill(testText);

    // Intercept and validate request
    const requestPromise = page.waitForRequest(/\/api\/todos/);
    await newTodoInput.press('Enter');

    const request = await requestPromise;
    const requestBody = await request.postDataJSON();

    // Validate request schema
    const validation = await validateSchema(
      requestBody,
      TodoCreateRequestSchema,
      'POST body'
    );
    expect(validation.success).toBe(true);

    expect(requestBody).toHaveProperty('text', testText);
    expect(Object.keys(requestBody)).toEqual(['text']);
  });

  test('verify no unintended response fields - security check', async ({ page }) => {
    const newTodoInput = page.locator('input.new-todo');
    await newTodoInput.fill('Security test');
    await newTodoInput.press('Enter');

    const response = await page.waitForResponse(/\/api\/todos/);
    const body = await response.json();

    // These fields should NOT be in the response
    const sensitiveFields = [
      'password', 'token', 'secret', 'apiKey',
      'internalId', 'hash', 'salt'
    ];

    const foundSensitiveFields = sensitiveFields.filter(
      field => field in body
    );

    if (foundSensitiveFields.length > 0) {
      throw new Error(
        `⚠️ SECURITY: Sensitive fields exposed: ${foundSensitiveFields.join(', ')}`
      );
    }

    expect(foundSensitiveFields.length).toBe(0);
  });

  test('response consistency - multiple requests', async ({ page }) => {
    const newTodoInput = page.locator('input.new-todo');
    const responses: typeof TodoSchema[] = [];

    // Create 3 todos
    for (let i = 1; i <= 3; i++) {
      await newTodoInput.fill(`Todo ${i}`);
      await newTodoInput.press('Enter');

      const response = await page.waitForResponse(/\/api\/todos/);
      const body = await response.json();
      responses.push(body);
    }

    // Verify all responses follow same schema
    for (const body of responses) {
      const validation = await validateSchema(body, TodoSchema, 'consistency');
      expect(validation.success).toBe(true);
    }

    // Verify IDs are unique
    const ids = responses.map(r => r.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });
});
