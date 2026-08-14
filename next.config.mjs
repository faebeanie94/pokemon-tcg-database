import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  // better-sqlite3 is a native module and must not be bundled by webpack/turbopack.
  serverExternalPackages: ["better-sqlite3"],
  // Smaller Fly image: only the traced server + static assets.
  output: "standalone",
  // Parent folders also have lockfiles; keep tracing rooted on this app.
  outputFileTracingRoot: __dirname,
  eslint: {
    // Parent ../.eslintrc.json conflicts with this package's config in monorepo layouts.
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
