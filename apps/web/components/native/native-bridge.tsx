"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { appVersion, isNativeApp, pushAvailable } from "@/lib/native";

/** Puente con la app móvil (feature 025): botón atrás de Android, registro de avisos y
 *  navegación al tocar un aviso. Solo actúa dentro de la app; en el navegador no hace nada. */
export function NativeBridge() {
  const pathname = usePathname();
  const pathRef = useRef(pathname);
  pathRef.current = pathname;

  useEffect(() => {
    if (!isNativeApp()) return;
    const removers: Array<() => Promise<void> | void> = [];
    let cancelled = false;

    (async () => {
      const { App } = await import("@capacitor/app");
      const back = await App.addListener("backButton", ({ canGoBack }) => {
        // En el Panorama (o sin historial) el botón atrás sale de la app, como en Android.
        if (pathRef.current === "/" || !canGoBack) void App.exitApp();
        else window.history.back();
      });
      removers.push(() => back.remove());

      if (!pushAvailable()) return;
      const { PushNotifications } = await import("@capacitor/push-notifications");
      const { Device } = await import("@capacitor/device");

      const reg = await PushNotifications.addListener("registration", async ({ value }) => {
        try {
          const info = await Device.getInfo();
          await api.registerPushDevice({
            token: value,
            platform: info.platform === "ios" ? "ios" : "android",
            model: [info.manufacturer, info.model].filter(Boolean).join(" ") || undefined,
            app_version: appVersion(),
          });
        } catch {
          // Sin conexión o sesión vencida: se reintenta en la próxima apertura.
        }
      });
      // Con la app abierta Android no muestra el aviso: se muestra dentro de la app.
      const received = await PushNotifications.addListener("pushNotificationReceived", (n) => {
        toast(n.title ?? "StayLever", { description: n.body });
      });
      const tapped = await PushNotifications.addListener("pushNotificationActionPerformed", (a) => {
        const url = a.notification.data?.url;
        if (typeof url === "string" && url.startsWith("/")) window.location.assign(url);
      });
      removers.push(() => reg.remove(), () => received.remove(), () => tapped.remove());
      if (cancelled) return;

      let perm = await PushNotifications.checkPermissions();
      if (perm.receive === "prompt" || perm.receive === "prompt-with-rationale") {
        perm = await PushNotifications.requestPermissions();
      }
      if (perm.receive !== "granted") return;
      await PushNotifications.createChannel({
        id: "staylever",
        name: "StayLever",
        description: "Reservas y sugerencias",
        importance: 4,
      }).catch(() => undefined);
      await PushNotifications.register();
    })().catch(() => undefined);

    return () => {
      cancelled = true;
      removers.forEach((r) => void r());
    };
  }, []);

  return null;
}
