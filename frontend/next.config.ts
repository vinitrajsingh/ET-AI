import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // A stray package-lock.json in the parent/home directory makes Turbopack guess
  // the wrong workspace root. Pin it explicitly to this project.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
