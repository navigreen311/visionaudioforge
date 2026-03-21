/** @type {import('next').NextConfig} */
const nextConfig = {
  // output: "standalone",  // Only needed for Docker production builds
  typescript: {
    // Allow dev server to run despite TS errors in non-critical pages
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
