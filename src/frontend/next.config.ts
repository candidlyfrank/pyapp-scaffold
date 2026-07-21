import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["pyapp.envx"],
  output: "standalone",
};

export default nextConfig;
