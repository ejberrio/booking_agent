import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Booking AI Agent",
  description: "Gestión inteligente de precios para Booking.com",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
