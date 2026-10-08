// Cookie de sesión firmada (HMAC-SHA256). Formato: "<expiración epoch s>.<firma base64url>".
// La clave se deriva de APP_PASSWORD: cambiar la contraseña invalida todas las sesiones.
// Solo usa Web Crypto, así funciona tanto en el middleware (Edge) como en las rutas (Node).

export const SESSION_COOKIE = "session";
export const SESSION_MAX_AGE = 60 * 60 * 24 * 7; // 7 días

const enc = new TextEncoder();

function b64url(buf: ArrayBuffer): string {
  let s = "";
  for (const b of new Uint8Array(buf)) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function sign(secret: string, payload: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(`booking-agent-session:${secret}`),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return b64url(await crypto.subtle.sign("HMAC", key, enc.encode(payload)));
}

export async function createSessionToken(secret: string, now = Date.now()): Promise<string> {
  const exp = String(Math.floor(now / 1000) + SESSION_MAX_AGE);
  return `${exp}.${await sign(secret, exp)}`;
}

export async function verifySessionToken(
  token: string | undefined,
  secret: string | undefined,
  now = Date.now(),
): Promise<boolean> {
  if (!token || !secret) return false;
  const [exp, sig, extra] = token.split(".");
  if (!exp || !sig || extra !== undefined || !/^\d+$/.test(exp)) return false;
  if (Number(exp) * 1000 <= now) return false;
  const expected = await sign(secret, exp);
  // Comparación en tiempo constante.
  if (expected.length !== sig.length) return false;
  let diff = 0;
  for (let i = 0; i < sig.length; i++) diff |= expected.charCodeAt(i) ^ sig.charCodeAt(i);
  return diff === 0;
}
