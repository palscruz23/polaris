# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: filter-focus.spec.js >> data browser filter keeps focus across row reloads
- Location: ../../../../../tmp/open-rel-pw/filter-focus.spec.js:3:1

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.waitForSelector: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('table.data-table') to be visible

```

# Page snapshot

```yaml
- main [ref=e2]:
  - generic [ref=e4]:
    - navigation [ref=e5]:
      - link "Open Reliability" [ref=e6] [cursor=pointer]:
        - /url: /
        - generic [ref=e7]: Open Reliability
      - link "Back home" [ref=e8] [cursor=pointer]:
        - /url: /
    - generic [ref=e9]:
      - heading "Existing data" [level=1] [ref=e10]
      - paragraph [ref=e11]: Browse the current Postgres tables that back Open Reliability.
  - complementary "Postgres tables" [ref=e14]:
    - generic [ref=e15]:
      - generic [ref=e16]: Tables
      - strong [ref=e17]: "0"
    - paragraph [ref=e18]: Loading tables...
```

# Test source

```ts
  1  | const { test, expect } = require("@playwright/test");
  2  |
  3  | test("data browser filter keeps focus across row reloads", async ({ page }) => {
  4  |   const messages = [];
  5  |   page.on("console", (msg) => messages.push(`${msg.type()}: ${msg.text()}`));
  6  |   page.on("pageerror", (error) => messages.push(`pageerror: ${error.message}`));
  7  |
  8  |   await page.setViewportSize({ width: 1440, height: 900 });
  9  |   await page.goto("http://127.0.0.1:3000/view-existing-data");
> 10 |   await page.waitForSelector("table.data-table");
     |              ^ Error: page.waitForSelector: Test timeout of 30000ms exceeded.
  11 |
  12 |   const input = page.locator(".data-filter-row input").first();
  13 |
  14 |   await input.click();
  15 |   await page.keyboard.type("P");
  16 |   await page.waitForTimeout(250);
  17 |   await expect(input).toBeFocused();
  18 |
  19 |   await page.keyboard.type("U");
  20 |   await page.waitForTimeout(900);
  21 |   await expect(input).toBeFocused();
  22 |   await expect(input).toHaveValue("PU");
  23 |
  24 |   await page.screenshot({
  25 |     path: "/tmp/open-reliability-filter-focus.png",
  26 |     fullPage: false,
  27 |   });
  28 |
  29 |   expect(messages.filter((message) => message.startsWith("error:"))).toEqual([]);
  30 | });
  31 |
```