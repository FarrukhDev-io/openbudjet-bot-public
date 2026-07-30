import { useEffect, useState } from "react";

export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
}

export function useTelegram() {
  const [user, setUser] = useState<TelegramUser | null>(null);

  const getTelegramWebApp = () => {
    if (typeof window !== "undefined") {
      return (window as any).Telegram?.WebApp || null;
    }
    return null;
  };

  useEffect(() => {
    const webApp = getTelegramWebApp();
    if (webApp) {
      webApp.ready();
      webApp.expand();
      webApp.enableClosingConfirmation();
      if (webApp.initDataUnsafe?.user) {
        setUser(webApp.initDataUnsafe.user);
      }
    }
  }, []);

  const triggerHaptic = (type: "light" | "medium" | "heavy" | "success" | "warning" | "error" = "medium") => {
    const webApp = getTelegramWebApp();
    if (!webApp?.HapticFeedback) return;

    if (type === "success" || type === "warning" || type === "error") {
      webApp.HapticFeedback.notificationOccurred(type);
    } else {
      webApp.HapticFeedback.impactOccurred(type);
    }
  };

  const closeWebApp = () => {
    const webApp = getTelegramWebApp();
    if (webApp) {
      webApp.close();
    }
  };

  const adminId = user?.id || 991729905; // Fallback to user's admin ID for local dev

  return {
    webApp: getTelegramWebApp(),
    user,
    adminId,
    triggerHaptic,
    closeWebApp,
  };
}
