/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  transpilePackages: ['@crewai/shared-types', '@crewai/ui'],
  experimental: {
    optimizePackageImports: ['@crewai/ui'],
  },
};

module.exports = nextConfig;