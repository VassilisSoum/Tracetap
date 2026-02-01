# E-commerce API Testing with TraceTap

This example demonstrates how to use TraceTap to capture e-commerce API traffic and generate AI-powered tests for checkout flows, product catalog, and order management.

## Overview

In this example, you will:
1. Capture live API traffic from an e-commerce workflow
2. Export captured traffic as raw JSON
3. Use Claude AI to generate comprehensive Playwright tests
4. Run tests against your API

## Prerequisites

```bash
# Install TraceTap (from project root)
pip install -e .

# Or install dependencies
pip install mitmproxy requests pyyaml
```

## Directory Structure

```
ecommerce-api/
├── README.md                    # This file
├── sample-api/
│   └── server.py               # Sample e-commerce API server
├── captured-traffic/
│   └── checkout-flow.json      # Captured checkout workflow
└── generated-tests/
    └── checkout.spec.ts        # AI-generated Playwright tests
```

## Quick Start

### Step 1: Start the Sample E-commerce API

First, run the included sample API server:

```bash
cd examples/ecommerce-api
python sample-api/server.py
```

The server runs on `http://localhost:5000` with these endpoints:
- `GET /products` - List all products
- `GET /products/{id}` - Get product details
- `POST /cart` - Add item to cart
- `GET /cart` - View cart contents
- `POST /checkout` - Process checkout
- `GET /orders/{id}` - Get order status

### Step 2: Capture API Traffic

In a new terminal, start TraceTap to capture traffic:

```bash
# From project root
tracetap capture --port 8080 \
    --output examples/ecommerce-api/captured-traffic/checkout-flow.json \
    --filter-host "localhost:5000"
```

### Step 3: Execute the Checkout Flow

With the proxy running, execute API calls through the proxy:

```bash
# Set proxy environment variables
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Browse products
curl -x http://localhost:8080 http://localhost:5000/products
curl -x http://localhost:8080 http://localhost:5000/products/1

# Add items to cart
curl -x http://localhost:8080 -X POST http://localhost:5000/cart \
    -H "Content-Type: application/json" \
    -d '{"product_id": 1, "quantity": 2}'

curl -x http://localhost:8080 -X POST http://localhost:5000/cart \
    -H "Content-Type: application/json" \
    -d '{"product_id": 3, "quantity": 1}'

# View cart
curl -x http://localhost:8080 http://localhost:5000/cart

# Checkout
curl -x http://localhost:8080 -X POST http://localhost:5000/checkout \
    -H "Content-Type: application/json" \
    -d '{"payment_method": "credit_card", "shipping_address": "123 Main St"}'

# Check order status
curl -x http://localhost:8080 http://localhost:5000/orders/1
```

Press `Ctrl+C` in the TraceTap terminal to stop capture and export.

### Step 4: Generate Tests with Claude AI

Use the captured JSON with Claude to generate comprehensive tests:

```bash
# Export the captured traffic
tracetap export checkout-flow.json --format json

# Then use Claude to generate tests
claude "Generate Playwright API tests from this captured traffic: $(cat checkout-flow.json)"
```

Or use Claude Code directly:

```
@checkout-flow.json Generate comprehensive Playwright API tests for this
e-commerce checkout flow. Include:
- Individual endpoint tests
- Full workflow test (browse -> cart -> checkout)
- Error handling scenarios
- Response validation
```

## Captured Traffic Format

The captured traffic JSON follows this structure:

```json
{
  "metadata": {
    "session_name": "ecommerce-checkout",
    "timestamp": "2024-01-20T10:30:00Z",
    "filter": "localhost:5000"
  },
  "requests": [
    {
      "method": "GET",
      "url": "http://localhost:5000/products",
      "status_code": 200,
      "timestamp": "2024-01-20T10:30:01Z",
      "duration_ms": 15,
      "headers": {},
      "body": null,
      "response_body": "[{\"id\": 1, \"name\": \"Laptop\", ...}]",
      "response_headers": {"Content-Type": "application/json"}
    }
  ]
}
```

## AI-Generated Tests

When you provide captured traffic to Claude, it generates tests like:

```typescript
import { test, expect } from '@playwright/test';

test.describe('E-commerce Checkout Flow', () => {
  const baseURL = 'http://localhost:5000';

  test('GET /products returns product list', async ({ request }) => {
    const response = await request.get(`${baseURL}/products`);
    expect(response.status()).toBe(200);

    const products = await response.json();
    expect(Array.isArray(products)).toBe(true);
    expect(products.length).toBeGreaterThan(0);
    expect(products[0]).toHaveProperty('id');
    expect(products[0]).toHaveProperty('name');
    expect(products[0]).toHaveProperty('price');
  });

  test('POST /cart adds item to cart', async ({ request }) => {
    const response = await request.post(`${baseURL}/cart`, {
      data: { product_id: 1, quantity: 2 }
    });
    expect(response.status()).toBe(200);

    const cart = await response.json();
    expect(cart.items).toContainEqual(
      expect.objectContaining({ product_id: 1, quantity: 2 })
    );
  });

  test('Complete checkout workflow', async ({ request }) => {
    // Step 1: Browse products
    const products = await request.get(`${baseURL}/products`);
    expect(products.status()).toBe(200);
    const productList = await products.json();

    // Step 2: Add to cart
    const addToCart = await request.post(`${baseURL}/cart`, {
      data: { product_id: productList[0].id, quantity: 2 }
    });
    expect(addToCart.status()).toBe(200);

    // Step 3: Checkout
    const checkout = await request.post(`${baseURL}/checkout`, {
      data: {
        payment_method: 'credit_card',
        shipping_address: '123 Main St'
      }
    });
    expect(checkout.status()).toBe(201);

    const order = await checkout.json();
    expect(order.id).toBeDefined();
    expect(order.status).toBe('confirmed');

    // Step 4: Verify order
    const orderStatus = await request.get(`${baseURL}/orders/${order.id}`);
    expect(orderStatus.status()).toBe(200);
  });
});
```

## Claude AI Prompts for Test Generation

### Basic Test Generation
```
Generate Playwright API tests from this traffic JSON.
Focus on status codes and response structure validation.
```

### Comprehensive Test Generation
```
Generate comprehensive Playwright API tests including:
1. Individual endpoint tests with assertions
2. Workflow tests that chain requests together
3. Edge case tests (invalid inputs, missing fields)
4. Response time assertions
5. Data validation for critical fields
```

### Regression Test Focus
```
Generate regression tests that will catch breaking changes:
- Schema changes (new/removed fields)
- Status code changes
- Response format changes
- Required field removal
```

## Real-World Integration

### With a Real E-commerce API

Replace the sample server with your actual API:

```bash
tracetap capture --port 8080 \
    --output captured-traffic/production.json \
    --filter-host "api.yourstore.com"
```

### CI/CD Integration

```yaml
# .github/workflows/api-tests.yml
- name: Run API Regression Tests
  run: |
    npx playwright test examples/ecommerce-api/generated-tests/
```

## Troubleshooting

### Certificate Issues
If you're capturing HTTPS traffic:
```bash
tracetap cert install
```

### Proxy Not Capturing
Ensure your client respects proxy settings:
```bash
curl -v -x http://localhost:8080 http://api.example.com/test
```

## Next Steps

- Explore the [Regression Suite Example](../regression-suite/) for automated test workflows
- Read the main [TraceTap documentation](../../README.md) for all features
