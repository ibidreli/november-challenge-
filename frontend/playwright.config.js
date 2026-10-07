import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
const python =
  process.env.PYTHON ||
  path.resolve(
    "..",
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  reporter: "list",
  use: { trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    {
      name: "desktop",
      testMatch: /ui\.spec\.js/,
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1000 },
        baseURL: "http://localhost:5178",
      },
    },
    {
      name: "mobile",
      testMatch: /ui\.spec\.js/,
      use: {
        ...devices["Pixel 7"],
        viewport: { width: 390, height: 844 },
        baseURL: "http://localhost:5178",
      },
    },
    {
      name: "integration",
      testMatch: /integration\.spec\.js/,
      use: { ...devices["Desktop Chrome"], baseURL: "http://localhost:5179" },
    },
    {
      name: "october",
      testMatch: /october\.spec\.js/,
      use: { ...devices["Desktop Chrome"], baseURL: "http://localhost:5180" },
    },
  ],
  webServer: [
    {
      command: "npm run dev:ui -- --port 5178",
      url: "http://localhost:5178",
      reuseExistingServer: false,
    },
    {
      command: `"${python}" ../backend/tests/serve_e2e.py`,
      url: "http://localhost:8021/healthz",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: "npx vite --mode test --port 5179",
      env: {
        VITE_API_PROXY_TARGET: "http://localhost:8021",
        VITE_UI_PREVIEW: "false",
        VITE_API_BASE_URL: "",
      },
      url: "http://localhost:5179",
      reuseExistingServer: false,
    },
    {
      command: `"${python}" ../backend/tests/serve_e2e.py`,
      env: { E2E_OCTOBER: "1" },
      url: "http://localhost:8022/healthz",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: "npx vite --mode test --port 5180",
      env: {
        VITE_API_PROXY_TARGET: "http://localhost:8022",
        VITE_UI_PREVIEW: "false",
        VITE_API_BASE_URL: "",
      },
      url: "http://localhost:5180",
      reuseExistingServer: false,
    },
  ],
});
