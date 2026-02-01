# E-commerce API Testing with TraceTap

This example demonstrates how to use TraceTap to capture, document, and test an e-commerce API including checkout flows, product catalog, and order management.

## Overview

In this example, you will:
1. Capture live API traffic from an e-commerce workflow
2. Generate a Postman collection from captured traffic
3. Create regression tests with Playwright
4. Set up contract testing for API validation
5. Run a mock server for offline development

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
├── generated-tests/
│   ├── regression.spec.ts      # Generated Playwright tests
│   └── postman-collection.json # Generated Postman collection
├── contracts/
│   └── ecommerce-api.yaml      # OpenAPI contract
└── scripts/
    ├── capture.sh              # Traffic capture script
    ├── generate-tests.sh       # Test generation script
    └── run-mock.sh             # Mock server script
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
python tracetap.py --listen 8080 \
    --export examples/ecommerce-api/captured-traffic/checkout-flow.json \
    --raw-log examples/ecommerce-api/captured-traffic/raw-traffic.json \
    --session "ecommerce-checkout" \
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

### Step 4: Generate Regression Tests

Generate Playwright tests from the captured traffic:

```bash
python tracetap-replay.py generate-regression \
    examples/ecommerce-api/captured-traffic/checkout-flow.json \
    -o examples/ecommerce-api/generated-tests/regression.spec.ts \
    --grouping flow \
    --base-url http://localhost:5000
```

### Step 5: Generate OpenAPI Contract

Create an API contract from traffic:

```bash
python tracetap-replay.py create-contract \
    examples/ecommerce-api/captured-traffic/checkout-flow.json \
    -o examples/ecommerce-api/contracts/ecommerce-api.yaml \
    --title "E-commerce API" \
    --version "1.0.0"
```

### Step 6: Run Mock Server

Start a mock server using captured responses:

```bash
python tracetap-replay.py mock \
    examples/ecommerce-api/captured-traffic/checkout-flow.json \
    --port 9000 \
    --matching fuzzy
```

Now you can develop against `http://localhost:9000` without the real API.

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

## Generated Tests

The generated Playwright tests include:

- **Status code assertions** - Verify correct HTTP status codes
- **Response structure validation** - Check required fields exist
- **Data type assertions** - Validate field types
- **Flow testing** - Test complete user workflows

Example generated test:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Checkout Flow', () => {
  const baseURL = 'http://localhost:5000';

  test('Complete checkout flow', async ({ request }) => {
    // Step 1: Browse products
    const products = await request.get(`${baseURL}/products`);
    expect(products.status()).toBe(200);
    const productList = await products.json();
    expect(productList).toBeInstanceOf(Array);

    // Step 2: Add to cart
    const addToCart = await request.post(`${baseURL}/cart`, {
      data: { product_id: 1, quantity: 2 }
    });
    expect(addToCart.status()).toBe(200);

    // Step 3: Checkout
    const checkout = await request.post(`${baseURL}/checkout`, {
      data: { payment_method: 'credit_card', shipping_address: '123 Main St' }
    });
    expect(checkout.status()).toBe(201);
    const order = await checkout.json();
    expect(order.id).toBeDefined();
    expect(order.status).toBe('confirmed');
  });
});
```

## Contract Testing

The generated OpenAPI contract enables:

1. **Schema validation** - Ensure responses match expected structure
2. **Breaking change detection** - Catch API changes before deployment
3. **Documentation** - Auto-generated API docs

Verify contract compliance:

```bash
# Compare baseline vs current contract
python tracetap-replay.py verify-contract \
    examples/ecommerce-api/contracts/baseline.yaml \
    examples/ecommerce-api/contracts/current.yaml \
    --fail-on-breaking
```

## Real-World Integration

### With a Real E-commerce API

Replace the sample server with your actual API:

```bash
python tracetap.py --listen 8080 \
    --export captured-traffic/production.json \
    --filter-host "api.yourstore.com"
```

### CI/CD Integration

Add to your pipeline:

```yaml
# .github/workflows/api-tests.yml
- name: Run API Regression Tests
  run: |
    npx playwright test examples/ecommerce-api/generated-tests/

- name: Verify API Contract
  run: |
    python tracetap-replay.py verify-contract \
      contracts/baseline.yaml contracts/current.yaml \
      --fail-on-breaking
```

## Troubleshooting

### Certificate Issues
If you're capturing HTTPS traffic:
```bash
python -m tracetap.cert_installer install
```

### Proxy Not Capturing
Ensure your client respects proxy settings:
```bash
curl -v -x http://localhost:8080 http://api.example.com/test
```

### Mock Server Matching
If the mock returns 404, try different matching modes:
```bash
# Exact matching
python tracetap-replay.py mock traffic.json --matching exact

# Fuzzy matching (handles ID differences)
python tracetap-replay.py mock traffic.json --matching fuzzy

# Pattern matching (regex-based)
python tracetap-replay.py mock traffic.json --matching pattern
```

## Next Steps

- Explore the [Regression Suite Example](../regression-suite/) for automated test workflows
- See [Contract Testing Example](../contract-testing/) for CI/CD integration
- Read the main [TraceTap documentation](../../README.md) for all features
