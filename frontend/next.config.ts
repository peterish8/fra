import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // Keep the interactive preview cache separate from `next build` output so a
  // production verification cannot corrupt an already-running local preview.
  distDir: process.env.NODE_ENV === "development" ? ".next-dev" : ".next",
  poweredByHeader: false,
  reactStrictMode: true,
  outputFileTracingRoot: path.join(process.cwd()),
};

export default nextConfig;
