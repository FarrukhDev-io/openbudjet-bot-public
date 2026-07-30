import { useEffect, useState } from "react";

export function useTelegram() {
  const [tg, setTg] = useState<any>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && (window as any).Telegram?.WebApp) {
      const webApp = (window as any).Telegram.WebApp;
      webApp.ready();
      webApp.expand();
      webApp.enableClosingConfirmation();
      setTg(webApp);
    }
  }, []);

  const user = tg?.initDataUnsafe?.user || null;
  const adminId = user?.id || 123456789; // Fallback for dev environment

  const triggerHaptic = (type: "light" | "medium" | "heavy" | "success" | "warning" | "error" = "medium") => {
    if (!tg?.HapticFeedback) return;
    try {
      if (["light", "medium", "heavy"].includes(type)) {
        tg.HapticFeedback.impactOccurred(type);
      } else if (["success", "warning", "error"].includes(type)) {
        tg.HapticFeedback.notificationOccurred(type);
      }
    } catch (e) {
      console.warn("Haptic feedback trigger failed:", e);
    }
  };

  const closeWebApp = () => {
    tg?.close();
  };

  return {
    tg,
    user,
    adminId,
    triggerHaptic,
    closeWebApp
  };
}
