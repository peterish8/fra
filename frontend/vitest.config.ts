import { defineConfig } from "vitest/config";

export default defineConfig({
  // tsconfig.json must keep "jsx": "preserve" for Next.js's own SWC
  // compiler (Next.js rewrites it back on every build otherwise), so Vite's
  // JSX transform for the test runner is set explicitly here instead.
  oxc: {
    jsx: { runtime: "automatic" },
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts", "tests/**/*.test.tsx"],
  },
});
