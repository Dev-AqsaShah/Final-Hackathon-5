/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';
    return [
      {
        source: '/api/support/:path*',
        destination: `${apiUrl}/support/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
