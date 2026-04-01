/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/support/:path*',
        destination: 'http://localhost:8002/support/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
