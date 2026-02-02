# E-commerce Checkout Example - Advanced Workflow

Learn advanced UI recording with a realistic e-commerce checkout flow.

## Overview

**Application:** Sample E-commerce Store
**Difficulty:** Intermediate
**Time:** 20-25 minutes
**Prerequisites:** Node.js 16+

## What You'll Learn

- Recording multi-step workflows
- Handling form validation
- Testing payment flows
- Cart state management
- Session-based testing

## Workflow Overview

This example records a complete e-commerce purchase:

1. **Browse Products** - View product catalog
2. **Add to Cart** - Add 2 items with different quantities
3. **View Cart** - Review items and adjust quantities
4. **Checkout** - Fill shipping and payment forms
5. **Order Confirmation** - Verify order placement

## Files Included

```
ecommerce/
├── README.md                          # This file
├── session-example/                   # Pre-recorded checkout session
│   ├── metadata.json                  # Session info
│   └── correlation.json               # UI + API correlations
├── generated-tests/
│   ├── basic.spec.ts                  # Basic template
│   ├── comprehensive.spec.ts          # Full validation
│   └── regression.spec.ts             # Contract testing
├── playwright.config.ts               # Playwright configuration
└── package.json                       # Test dependencies
```

## Session Overview

### Recorded Actions

**Action 1: Browse Products**
- Click "Shop" or "Products"
- Wait for product list to load
- Click on a product (e.g., Laptop)

**Action 2: View Product Details**
- Verify product image loads
- Check price display
- Read description

**Action 3: Add First Item**
- Set quantity to 2
- Click "Add to Cart"
- Verify success message

**Action 4: Add Second Item**
- Go back to products
- Select a different item (e.g., Mouse)
- Set quantity to 1
- Click "Add to Cart"

**Action 5: View Cart**
- Click "Cart" or "View Cart"
- Verify both items displayed
- Check total price calculation

**Action 6: Checkout**
- Click "Checkout"
- Fill shipping form:
  - Name: John Doe
  - Email: john@example.com
  - Address: 123 Main St
  - City: Springfield
  - ZIP: 12345
- Fill payment form:
  - Card: 4242 4242 4242 4242
  - Expiry: 12/25
  - CVC: 123

**Action 7: Order Confirmation**
- Verify "Order Placed" message
- Check order number displayed
- Review order summary

## Session Statistics

- **Duration:** 2 minutes 15 seconds
- **UI Events:** 18
- **Network Calls:** 12
- **Correlation Rate:** 78%
- **Average Confidence:** 0.85

## Correlation Analysis

High-confidence correlations (90%+):
- Add to cart clicks → POST /api/cart
- Form submissions → POST /api/checkout
- Quantity updates → PATCH /api/cart/:id

Medium-confidence (70-90%):
- Product clicks → GET /api/products/:id
- View cart clicks → GET /api/cart

Low-confidence (<70%):
- Page navigation (client-side only)
- Product filtering (no API)

## Advanced Testing Features

### State Management Testing

```typescript
test('verify cart state persists across navigation', async ({ page }) => {
  // Add items
  await addToCart('Laptop', 1);
  await addToCart('Mouse', 2);

  // Navigate away
  await page.click('a:has-text("Home")');

  // Navigate back to cart
  await page.click('a:has-text("Cart")');

  // Verify items still there
  await expect(page.locator('text=Laptop')).toBeVisible();
  await expect(page.locator('text=Mouse')).toBeVisible();
});
```

### Form Validation Testing

```typescript
test('reject invalid email in checkout', async ({ page }) => {
  await page.fill('input[name="email"]', 'invalid-email');
  await page.click('button:has-text("Continue")');

  // Verify error message
  await expect(page.locator('text=Invalid email')).toBeVisible();

  // Verify form not submitted
  let callCount = 0;
  page.on('response', (response) => {
    if (response.url().includes('/api/checkout')) callCount++;
  });

  expect(callCount).toBe(0);
});
```

### Payment Simulation Testing

```typescript
test('simulate payment processing', async ({ page }) => {
  // Fill payment details
  const cardNumber = '4242 4242 4242 4242';
  await page.fill('input[name="cardNumber"]', cardNumber);
  await page.fill('input[name="expiry"]', '12/25');
  await page.fill('input[name="cvc"]', '123');

  // Submit
  await page.click('button:has-text("Pay Now")');

  // Verify processing
  await expect(page.locator('text=Processing')).toBeVisible({ timeout: 5000 });

  // Wait for success
  const response = await page.waitForResponse('/api/checkout');
  expect(response.status()).toBe(201);
});
```

## Record Your Own Checkout

Want to record your own e-commerce session?

```bash
# 1. Start a local e-commerce demo
cd examples/ecommerce
npm run server

# 2. In another terminal, record
tracetap record http://localhost:3000 -n my-checkout

# 3. Complete a checkout flow:
#    - Browse products
#    - Add 2+ items
#    - Go to checkout
#    - Fill forms with test data
#    - Confirm order

# 4. Press Enter when done

# 5. Generate tests
tracetap-generate-tests recordings/<your-session-id> \
  -o generated-tests/my-checkout.spec.ts \
  --template comprehensive
```

## Template Selection Guide

**For Smoke Tests (Basic):**
- Quick CI/CD validation
- Check main flow doesn't break
- 2-3 minute execution

**For Regression Suite (Comprehensive):**
- Full workflow testing
- Validate all steps
- ~10 minute execution

**For Contract Testing (Regression):**
- Detect API changes
- Monitor data schema
- Verify SLAs

## Troubleshooting

### "Payment Failed" Messages

**Issue:** Test fails at payment step
**Solutions:**
- Verify using test card 4242 4242 4242 4242
- Check Stripe/payment provider test mode enabled
- Ensure amount is in cents (e.g., 9999 for $99.99)

### Form Fields Not Filling

**Issue:** Locators don't match actual form
**Solutions:**
- Inspect page to find correct selectors
- Use `test:ui` mode to debug
- Re-record with current app

### Cart Items Not Persisting

**Issue:** Items disappear on navigation
**Solutions:**
- Check localStorage/sessionStorage configured
- Verify cookies enabled
- Check API is returning persisted state

### Flaky Checkout Response

**Issue:** Test fails intermittently
**Solutions:**
- Increase timeout: `waitForResponse(pattern, { timeout: 10000 })`
- Add waits for spinners: `waitForLoadState('networkidle')`
- Check payment provider rate limiting

## Next Steps

1. ✅ Run the pre-generated tests
2. ✅ Review the checkout flow
3. ✅ Understand form validation testing
4. ✅ Study payment simulation patterns
5. ✅ Record your own checkout flow
6. ⏭️ Move to [Auth Flow Example](../auth/)

## Real-World Integration

### With Actual Shopify Store

```bash
tracetap record https://your-store.myshopify.com \
  -n shopify-checkout

# Then generate tests for your Shopify flow
```

### With Custom Store Platform

```bash
# Proxy through mitmproxy to capture HTTPS
tracetap record https://shop.example.com \
  -n custom-store \
  --proxy localhost:8080
```

## CI/CD Integration Example

```yaml
# .github/workflows/e-commerce-tests.yml
name: E-commerce Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: npm install

      - name: Start app server
        run: npm run start &
        env:
          DATABASE_URL: postgres://test:test@localhost/test

      - name: Wait for server
        run: sleep 5

      - name: Run e-commerce tests
        run: npx playwright test

      - name: Upload results
        uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

## Support

- [Getting Started Guide](../../../docs/getting-started/UI_RECORDING.md)
- [Form Handling Guide](../../../docs/guides/form-testing.md)
- [API Mocking Guide](../../../docs/guides/api-mocking.md)
