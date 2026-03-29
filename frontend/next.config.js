/** @type {import('next').NextConfig} */

// API_URL  → server-side only (not exposed to browser), used for rewrites
// NEXT_PUBLIC_API_URL → also available client-side (for direct fetch if needed)
// Rewrite destination is evaluated at Next.js server startup, so runtime env vars work fine.
const API_BASE =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

const nextConfig = {
  // Required on Render: Next.js must bind to $PORT
  // `next start -p $PORT` is set in package.json start script.

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_BASE}/api/:path*`,
      },
    ];
  },

  // Useful for Docker / Render standalone builds (reduces image size)
  // output: "standalone",  // uncomment if you want standalone mode
};

module.exports = nextConfig;
