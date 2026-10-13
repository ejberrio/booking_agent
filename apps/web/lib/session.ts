// Sesión por usuario (feature 026): la cookie httpOnly `sl_session` guarda un token opaco que
// la API valida en cada petición (sesiones revocables en el servidor). La web no firma nada:
// el middleware solo comprueba que la cookie exista y tenga forma de token.

export const SESSION_COOKIE = "sl_session";
/** Cookie de la versión anterior (contraseña compartida): se borra al entrar o salir. */
export const LEGACY_COOKIE = "session";
export const SESSION_MAX_AGE = 60 * 60 * 24 * 7; // 7 días
/** Sesión iniciada desde la app móvil (feature 025): 90 días. */
export const APP_SESSION_MAX_AGE = 60 * 60 * 24 * 90;
/** Marca que la app de Capacitor añade al User-Agent (capacitor.config: appendUserAgent). */
export const APP_USER_AGENT_MARK = "StayLeverApp/";

export type SessionKind = "web" | "app";

export function sessionKindFor(userAgent: string | null | undefined): SessionKind {
  return userAgent?.includes(APP_USER_AGENT_MARK) ? "app" : "web";
}

export function sessionMaxAgeFor(userAgent: string | null | undefined): number {
  return sessionKindFor(userAgent) === "app" ? APP_SESSION_MAX_AGE : SESSION_MAX_AGE;
}

/** ¿Tiene forma de token de sesión? (base64url de 32 bytes = 43 caracteres). */
export function looksLikeSessionToken(token: string | undefined): boolean {
  return !!token && /^[A-Za-z0-9_-]{40,64}$/.test(token);
}
