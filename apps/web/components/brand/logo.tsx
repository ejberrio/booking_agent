import { useId } from "react";

/** Logo original de la app (casa + piscina + destello de IA). Mismo dibujo que app/icon.svg. */
export function Logo({ size = 28, className }: { size?: number; className?: string }) {
  const gradient = `logo-${useId()}`;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradient} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#2563eb" />
          <stop offset="1" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="14" fill={`url(#${gradient})`} />
      <path
        d="M13 31 32 15l19 16"
        fill="none"
        stroke="#fff"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M19 28v16h26V28"
        fill="none"
        stroke="#fff"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M32 29.5l1.7 4.8 4.8 1.7-4.8 1.7-1.7 4.8-1.7-4.8-4.8-1.7 4.8-1.7z" fill="#fde68a" />
      <path
        d="M12 52q5-4 10 0t10 0 10 0 10 0"
        fill="none"
        stroke="#a5f3fc"
        strokeWidth="3.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
