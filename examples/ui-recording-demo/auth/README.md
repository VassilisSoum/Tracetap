# Authentication Flow Example - Session Management

Learn session and authentication testing with a real login/logout workflow.

## Overview

**Application:** Sample Auth App
**Difficulty:** Intermediate
**Time:** 15-20 minutes
**Prerequisites:** Understanding of tokens and sessions

## What You'll Learn

- Recording login flows
- Testing session persistence
- Validating authentication tokens
- Testing logout flows
- Protected route handling

## Workflow Overview

This example records a complete authentication cycle:

1. **Access Protected Route** - Try to view dashboard
2. **Redirected to Login** - Verify redirect to /login
3. **Enter Credentials** - Fill username and password
4. **Submit Login Form** - Click login button
5. **Receive Token** - Check token in response
6. **Access Dashboard** - View protected content
7. **Logout** - Click logout button
8. **Session Cleared** - Verify token removed

## Files Included

```
auth/
├── README.md                          # This file
├── session-example/                   # Pre-recorded auth session
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

**Action 1: Access Dashboard**
- Navigate to https://auth.example.com/dashboard
- App detects missing authentication
- Redirects to /login

**Action 2: View Login Form**
- Form loads with email and password fields
- Verify form is visible and interactive

**Action 3: Enter Credentials**
- Email: test@example.com
- Password: password123

**Action 4: Submit Login**
- Click "Login" button
- Wait for authentication response

**Action 5: Receive Token**
- API returns JWT token
- Token stored in localStorage or cookie
- User redirected to dashboard

**Action 6: View Protected Page**
- Dashboard loads successfully
- User data displayed
- Session confirmed active

**Action 7: Logout**
- Click "Logout" or "Sign out" button
- Session destroyed server-side
- Token cleared client-side

**Action 8: Verify Logout**
- Redirected to login or home page
- No token in storage
- Cannot access protected routes

## Session Statistics

- **Duration:** 1 minute 30 seconds
- **UI Events:** 8
- **Network Calls:** 5
- **Correlation Rate:** 85%
- **Average Confidence:** 0.87

## Correlation Insights

### High-Confidence Correlations (90%+)
- Login form submission → POST /api/auth/login
- Logout click → POST /api/auth/logout
- Token verification → GET /api/user (with token)

### Medium-Confidence (70-90%)
- Navigation to protected routes → redirect check
- Form field changes → no API (client-side)

### Special Case: Redirect Events
- Automatic redirects are client-side only
- Correlation looks for subsequent API calls
- Login success verified by token in response

## Authentication Testing Patterns

### Testing Login with Token

```typescript
test('login sets authentication token', async ({ page }) => {
  await page.goto('http://auth.example.com/login');

  // Fill credentials
  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('input[name="password"]', 'password123');

  // Submit form
  await page.click('button:has-text("Login")');

  // Wait for login response
  const response = await page.waitForResponse('/api/auth/login');
  expect(response.status()).toBe(200);

  const body = await response.json();
  expect(body).toHaveProperty('token');
  expect(body).toHaveProperty('user');

  // Verify token stored
  const token = await page.evaluate(() => localStorage.getItem('authToken'));
  expect(token).toBeTruthy();
});
```

### Testing Session Persistence

```typescript
test('user session persists on page reload', async ({ page, context }) => {
  // Login
  await page.goto('http://auth.example.com/login');
  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('input[name="password"]', 'password123');
  await page.click('button:has-text("Login")');

  const loginResponse = await page.waitForResponse('/api/auth/login');
  const { token } = await loginResponse.json();

  // Reload page
  await page.reload();

  // Verify still authenticated
  const dashboardResponse = await page.waitForResponse(
    response => response.url().includes('/api/user')
  );
  expect(dashboardResponse.status()).toBe(200);

  // Verify can access protected content
  await expect(page.locator('text=Dashboard')).toBeVisible();
});
```

### Testing Protected Routes

```typescript
test('unauthenticated users redirected from protected routes', async ({ page }) => {
  // Clear any existing tokens
  await page.evaluate(() => localStorage.removeItem('authToken'));

  // Try to access dashboard
  await page.goto('http://auth.example.com/dashboard');

  // Expect redirect to login
  expect(page.url()).toContain('/login');
  await expect(page.locator('text=Please log in')).toBeVisible();
});
```

### Testing Logout

```typescript
test('logout clears session and token', async ({ page }) => {
  // Login first
  await login(page);

  // Verify authenticated
  let token = await page.evaluate(() => localStorage.getItem('authToken'));
  expect(token).toBeTruthy();

  // Logout
  await page.click('button:has-text("Logout")');
  await page.waitForResponse('/api/auth/logout');

  // Verify token cleared
  token = await page.evaluate(() => localStorage.getItem('authToken'));
  expect(token).toBeNull();

  // Verify redirected to login
  expect(page.url()).toContain('/login');
});
```

### Testing Invalid Credentials

```typescript
test('invalid credentials show error', async ({ page }) => {
  await page.goto('http://auth.example.com/login');

  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('input[name="password"]', 'wrongpassword');

  await page.click('button:has-text("Login")');

  const response = await page.waitForResponse('/api/auth/login');
  expect(response.status()).toBe(401);

  // Verify error message shown
  await expect(page.locator('text=Invalid credentials')).toBeVisible();

  // Verify no token set
  const token = await page.evaluate(() => localStorage.getItem('authToken'));
  expect(token).toBeNull();
});
```

### Testing Token Expiration

```typescript
test('expired token refreshes automatically', async ({ page }) => {
  await login(page);

  // Simulate token expiration
  await page.evaluate(() => {
    const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE1MTYyMzkyMjJ9.invalid';
    localStorage.setItem('authToken', expiredToken);
  });

  // Make authenticated request
  const response = await page.waitForResponse(
    response => response.url().includes('/api/') && response.status() === 401
  );

  // Should trigger refresh flow
  expect(response.status()).toBe(401);

  // Token should be cleared after failed refresh
  const token = await page.evaluate(() => localStorage.getItem('authToken'));
  expect(token).toBeNull();
});
```

## Record Your Own Auth Flow

```bash
# 1. Start your auth app
npm run start

# 2. Record the auth flow
tracetap record http://localhost:3000 -n my-auth-flow

# 3. Complete the workflow:
#    - Navigate to protected route
#    - Get redirected to login
#    - Enter test@example.com / password123
#    - Submit login
#    - View dashboard
#    - Click logout
#    - Verify redirected

# 4. Press Enter when done

# 5. Generate tests
tracetap-generate-tests recordings/<your-session-id> \
  -o generated-tests/my-auth.spec.ts \
  --template comprehensive
```

## Security Testing

### Token Validation

```typescript
test('token has valid JWT structure', async ({ page }) => {
  const response = await login(page);
  const { token } = await response.json();

  // Verify JWT structure (header.payload.signature)
  const parts = token.split('.');
  expect(parts).toHaveLength(3);

  // Decode payload
  const payload = JSON.parse(
    Buffer.from(parts[1], 'base64').toString()
  );

  // Verify claims
  expect(payload).toHaveProperty('exp'); // expiration
  expect(payload).toHaveProperty('iat'); // issued at
  expect(payload).toHaveProperty('user_id');
});
```

### CSRF Protection

```typescript
test('login requires CSRF token', async ({ page }) => {
  await page.goto('http://auth.example.com/login');

  // Get CSRF token from page
  const csrfToken = await page.locator(
    'input[name="_csrf"]'
  ).inputValue();
  expect(csrfToken).toBeTruthy();

  // CSRF token should be included in request
  const requestPromise = page.waitForRequest(
    req => req.url().includes('/api/auth/login')
  );
  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('input[name="password"]', 'password123');
  await page.click('button:has-text("Login")');

  const request = await requestPromise;
  const body = await request.postDataJSON();
  expect(body).toHaveProperty('_csrf', csrfToken);
});
```

## Troubleshooting

### "Token Not Found" Error

**Issue:** Test can't find token in response
**Solutions:**
- Check response body format in login endpoint
- Token might be in header vs body
- Verify using `await response.json()`

### "Session Not Persisting"

**Issue:** Token disappears after page reload
**Solutions:**
- Check localStorage/sessionStorage is enabled
- Verify cookie settings (path, domain, secure)
- Check token TTL isn't expired

### "Protected Route Still Accessible"

**Issue:** Can access /dashboard without token
**Solutions:**
- Verify authentication middleware enabled
- Check token validation in route guards
- Ensure localStorage token is used

### "Redirect Not Happening"

**Issue:** Not redirected to /login after logout
**Solutions:**
- Check logout endpoint clears session
- Verify client-side redirect logic
- Check middleware order

## Next Steps

1. ✅ Run the pre-generated tests
2. ✅ Review the authentication flow
3. ✅ Study session management testing
4. ✅ Understand token validation patterns
5. ✅ Record your own auth flow
6. ⏭️ Build a custom example

## Advanced Topics

### Multi-Factor Authentication

```typescript
test('login with MFA flow', async ({ page }) => {
  await page.goto('http://auth.example.com/login');

  // Enter credentials
  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('input[name="password"]', 'password123');
  await page.click('button:has-text("Login")');

  // Should show MFA prompt
  await expect(page.locator('text=Verify with code')).toBeVisible();

  // Enter MFA code
  await page.fill('input[name="code"]', '123456');
  await page.click('button:has-text("Verify")');

  // Should complete login
  const response = await page.waitForResponse('/api/auth/verify-mfa');
  expect(response.status()).toBe(200);
});
```

### Social Login

```typescript
test('login via Google OAuth', async ({ page, context }) => {
  await page.goto('http://auth.example.com/login');

  // Click Google login
  await page.click('button:has-text("Sign in with Google")');

  // Handle OAuth popup
  const popupPromise = context.waitForEvent('page');
  const popup = await popupPromise;

  // Google auth flow (in popup)
  // This would be handled by your OAuth provider

  // Return to main app
  await popup.close();

  // Should be authenticated
  await expect(page.locator('text=Dashboard')).toBeVisible();
});
```

## Support

- [Getting Started Guide](../../../docs/getting-started/UI_RECORDING.md)
- [Authentication Guide](../../../docs/guides/authentication.md)
- [Security Testing](../../../docs/guides/security-testing.md)
