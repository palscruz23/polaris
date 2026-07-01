import type { NextConfig } from "next";

const apiProxyOrigin = process.env.API_PROXY_ORIGIN?.replace(/\/$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    if (!apiProxyOrigin) {
      return [];
    }

    return [
      {
        source: "/auth/:path*",
        destination: `${apiProxyOrigin}/auth/:path*`,
      },
      {
        source: "/conversations/:path*",
        destination: `${apiProxyOrigin}/conversations/:path*`,
      },
      {
        source: "/feedback/:path*",
        destination: `${apiProxyOrigin}/feedback/:path*`,
      },
      {
        source: "/models/:path*",
        destination: `${apiProxyOrigin}/models/:path*`,
      },
      {
        source: "/data-browser/:path*",
        destination: `${apiProxyOrigin}/data-browser/:path*`,
      },
      {
        source: "/defect-elimination/:path*",
        destination: `${apiProxyOrigin}/defect-elimination/:path*`,
      },
      {
        source: "/admin/evaluations/:path*",
        destination: `${apiProxyOrigin}/admin/evaluations/:path*`,
      },
      {
        source: "/admin/users/:path*",
        destination: `${apiProxyOrigin}/admin/users/:path*`,
      },
      {
        source: "/admin/feedback/:path*",
        destination: `${apiProxyOrigin}/admin/feedback/:path*`,
      },
    ];
  },
};

export default nextConfig;
