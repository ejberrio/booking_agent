#!/usr/bin/env bash
# Configura (una sola vez) los secretos de GitHub para construir el APK de StayLever (feature 025).
# - Crea la llave de firma del APK (si no existe) en ~/.staylever/ — FUERA del repo (es público).
# - Carga en GitHub: ANDROID_KEYSTORE_B64, ANDROID_KEYSTORE_PASSWORD, ANDROID_KEY_ALIAS,
#   ANDROID_KEY_PASSWORD y, si le pasas el archivo, GOOGLE_SERVICES_JSON.
# Las contraseñas las escribes tú; el script nunca las muestra ni las guarda en disco.
#
# Uso:  bash scripts/mobile/setup-android-secrets.sh [ruta/a/google-services.json]
set -euo pipefail

REPO="ejberrio/booking_agent"
DIR="$HOME/.staylever"
KEYSTORE="$DIR/staylever-release.keystore"
ALIAS="staylever"

command -v gh >/dev/null || { echo "Falta GitHub CLI: brew install gh && gh auth login"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Inicia sesión en GitHub: gh auth login"; exit 1; }

KEYTOOL="$(command -v keytool || true)"
if ! "$KEYTOOL" -help >/dev/null 2>&1; then
  for p in /opt/homebrew/opt/openjdk@21/bin/keytool /usr/local/opt/openjdk@21/bin/keytool; do
    [ -x "$p" ] && KEYTOOL="$p" && break
  done
fi
if ! "$KEYTOOL" -help >/dev/null 2>&1; then
  echo "Falta Java (keytool). Instálalo con:  brew install openjdk@21"
  exit 1
fi

mkdir -p "$DIR" && chmod 700 "$DIR"

read -r -s -p "Contraseña para la llave de firma (mín. 8 caracteres; guárdala en tu gestor): " PASS; echo
read -r -s -p "Repite la contraseña: " PASS2; echo
[ "$PASS" = "$PASS2" ] || { echo "No coinciden."; exit 1; }
[ "${#PASS}" -ge 8 ] || { echo "Mínimo 8 caracteres."; exit 1; }
export PASS  # keytool la lee del entorno (-storepass:env), nunca por línea de comandos

if [ -f "$KEYSTORE" ]; then
  echo "Ya existe $KEYSTORE: se reutiliza (las actualizaciones deben firmarse con la misma llave)."
  "$KEYTOOL" -list -keystore "$KEYSTORE" -storepass:env PASS -alias "$ALIAS" >/dev/null \
    || { echo "La contraseña no abre la llave existente."; exit 1; }
else
  "$KEYTOOL" -genkeypair -v -keystore "$KEYSTORE" -alias "$ALIAS" -keyalg RSA -keysize 2048 \
    -validity 10000 -storepass:env PASS -keypass:env PASS \
    -dname "CN=StayLever, O=StayLever, C=CO" >/dev/null
  chmod 600 "$KEYSTORE"
  echo "Llave creada en $KEYSTORE — HAZ UNA COPIA DE SEGURIDAD (sin ella no podrás actualizar la app)."
fi

base64 < "$KEYSTORE" | tr -d '\n' | gh secret set ANDROID_KEYSTORE_B64 --repo "$REPO"
printf '%s' "$PASS" | gh secret set ANDROID_KEYSTORE_PASSWORD --repo "$REPO"
printf '%s' "$PASS" | gh secret set ANDROID_KEY_PASSWORD --repo "$REPO"
printf '%s' "$ALIAS" | gh secret set ANDROID_KEY_ALIAS --repo "$REPO"

echo "Huella SHA-1 de la llave (para restringir la clave de Firebase, ver docs/mobile.md):"
"$KEYTOOL" -list -v -keystore "$KEYSTORE" -alias "$ALIAS" -storepass:env PASS 2>/dev/null | grep -E "SHA1:" || true
unset PASS PASS2

if [ "${1:-}" != "" ]; then
  [ -f "$1" ] || { echo "No existe $1"; exit 1; }
  gh secret set GOOGLE_SERVICES_JSON --repo "$REPO" < "$1"
  echo "GOOGLE_SERVICES_JSON cargado (avisos activados en el próximo APK)."
fi

echo "Listo. Secretos cargados en $REPO. Ahora: GitHub → Actions → Android APK → Run workflow."
