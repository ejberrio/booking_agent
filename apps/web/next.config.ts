import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Imagen de producción liviana (server.js autocontenido) para Railway.
  // CD activo: push a main -> redeploy automático.
  output: "standalone",
};

export default nextConfig;
