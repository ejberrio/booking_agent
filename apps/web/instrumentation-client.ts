import * as Sentry from "@sentry/nextjs";

// Init de Sentry en el navegador. No-op si no hay DSN.
const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
if (dsn) {
  Sentry.init({
    dsn,
    tracesSampleRate: 0, // v1: solo errores
  });
}

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
