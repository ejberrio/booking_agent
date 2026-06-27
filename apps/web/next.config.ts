import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Imagen de producción liviana (server.js autocontenido) para Railway.
  output: "standalone",
};

export default nextConfig;
