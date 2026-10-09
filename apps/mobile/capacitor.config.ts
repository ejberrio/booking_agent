import type { CapacitorConfig } from "@capacitor/cli";
import { existsSync } from "node:fs";

// App móvil de StayLever (feature 025): WebView nativo que carga la web real.
// - Una sola interfaz (la web): sus mejoras llegan sin reinstalar la app.
// - User-Agent "StayLeverApp/<versión>": la web da sesión de 90 días y activa el puente nativo;
//   " push" solo si el APK se construyó con Firebase (sin eso, registrar avisos cerraría la app).
const version = process.env.APP_VERSION ?? "1.0.0";
const hasPush = existsSync("android/app/google-services.json");

const config: CapacitorConfig = {
  appId: "com.staylever.app",
  appName: "StayLever",
  webDir: "www",
  appendUserAgent: `StayLeverApp/${version}${hasPush ? " push" : ""}`,
  server: {
    url: "https://staylever.com",
    // Página local si staylever.com no responde (sin conexión).
    errorPath: "offline.html",
  },
  android: {
    allowMixedContent: false,
  },
  plugins: {
    PushNotifications: {
      presentationOptions: ["badge", "sound", "alert"],
    },
  },
};

export default config;
