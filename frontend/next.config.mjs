/** @type {import('next').NextConfig} */
const nextConfig = {
  // output: "standalone",  // Only needed for Docker production builds
  //
  // NOTE: typescript.ignoreBuildErrors is deliberately NOT set. The tree is
  // type-clean and CI runs `tsc --noEmit` as a blocking job — re-adding the
  // suppression would let type errors accumulate silently again.
};

export default nextConfig;
