/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required by frontend/Dockerfile, which copies .next/standalone and runs
  // `node server.js`. It was commented out as "only needed for Docker
  // production builds" — but that is exactly the build the Dockerfile does, so
  // the frontend image could never be built. Enabling it unconditionally costs
  // `next dev` nothing; standalone output is only emitted by `next build`.
  output: "standalone",
  //
  // NOTE: typescript.ignoreBuildErrors is deliberately NOT set. The tree is
  // type-clean and CI runs `tsc --noEmit` as a blocking job — re-adding the
  // suppression would let type errors accumulate silently again.
};

export default nextConfig;
