// Genera los PNG de origen (assets/) para @capacitor/assets desde el logo de StayLever.
import sharp from "sharp";
import { readFileSync } from "node:fs";

const logo = readFileSync(new URL("../../web/app/icon.svg", import.meta.url), "utf8");
const glyph = logo
  .replace(/<rect[^>]*\/>/, "") // sin el fondo
  .replace(/<svg ([^>]*)>/, '<svg $1 width="64" height="64">');
const gradient = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2563eb"/><stop offset="1" stop-color="#06b6d4"/></linearGradient></defs><rect width="64" height="64" fill="url(#g)"/></svg>`;

const png = (svg, size) => sharp(Buffer.from(svg), { density: 1200 }).resize(size, size).png();

await png(logo, 1024).toFile("assets/icon-only.png");
await png(gradient, 1024).toFile("assets/icon-background.png");
// Primer plano adaptable: el dibujo ocupa ~60 % (zona segura de Android).
const fg = await png(glyph, 620).toBuffer();
await sharp({ create: { width: 1024, height: 1024, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
  .composite([{ input: fg, gravity: "center" }])
  .png()
  .toFile("assets/icon-foreground.png");
const splashLogo = await png(logo, 640).toBuffer();
for (const name of ["splash.png", "splash-dark.png"]) {
  await sharp({ create: { width: 2732, height: 2732, channels: 4, background: "#0a0a0a" } })
    .composite([{ input: splashLogo, gravity: "center" }])
    .png()
    .toFile(`assets/${name}`);
}
console.log("assets/ listo");
