import { defineConfig } from '@playwright/test';

// Uses the Edge already installed on the machine rather than downloading
// a Playwright browser bundle, so `npx playwright install` is not a
// prerequisite for running these.
export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false, // the fixtures share a port range
  reporter: process.env.CI ? 'list' : [['list']],
  use: {
    channel: 'msedge',
    headless: true,
    trace: 'retain-on-failure',
  },
});
