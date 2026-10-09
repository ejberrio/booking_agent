// Integración con la app móvil (Capacitor, feature 025). La app carga staylever.com en un
// WebView y añade al User-Agent "StayLeverApp/<versión>" (+ " push" si se construyó con
// Firebase). Fuera de la app todo esto es no-op.
import { APP_USER_AGENT_MARK } from "@/lib/session";

type CapacitorGlobal = { isNativePlatform?: () => boolean; getPlatform?: () => string };

export function isNativeApp(): boolean {
  if (typeof window === "undefined") return false;
  const cap = (window as unknown as { Capacitor?: CapacitorGlobal }).Capacitor;
  return Boolean(cap?.isNativePlatform?.()) || navigator.userAgent.includes(APP_USER_AGENT_MARK);
}

/** Versión de la app según el User-Agent ("StayLeverApp/1.2.0" → "1.2.0"). */
export function appVersion(): string | undefined {
  if (typeof navigator === "undefined") return undefined;
  return new RegExp(`${APP_USER_AGENT_MARK}([\\w.-]+)`).exec(navigator.userAgent)?.[1];
}

/** ¿La app se construyó con avisos (Firebase)? Sin eso, registrar avisos cerraría la app. */
export function pushAvailable(): boolean {
  if (typeof navigator === "undefined") return false;
  return new RegExp(`${APP_USER_AGENT_MARK}[\\w.-]+ push`).test(navigator.userAgent);
}
