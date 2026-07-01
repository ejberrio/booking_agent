import * as Sentry from "@sentry/nextjs";

// Init de Sentry en el servidor de Next. No-op si no hay DSN.
export function register() {
  const dsn = process.env.SENTRY_DSN;
  if (dsn && process.env.NEXT_RUNTIME === "nodejs") {
    Sentry.init({
      dsn,
      environment: process.env.ENVIRONMENT ?? "production",
      tracesSampleRate: 0, // v1: solo errores
    });
  }
}

// Captura de errores de request del servidor (Next 15).
export const onRequestError = Sentry.captureRequestError;
