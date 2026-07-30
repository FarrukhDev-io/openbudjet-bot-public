const tg = (window as any).Telegram?.WebApp;

export function useTelegram() {
  const adminId: number | null = tg?.initDataUnsafe?.user?.id ?? null;

  const expand = () => tg?.expand();
  const close = () => tg?.close();
  const ready = () => tg?.ready();

  const triggerHaptic = (
    type: "light" | "medium" | "heavy" | "success" | "warning" | "error" = "medium"
  ) => {
    if (!tg?.HapticFeedback) return;
    if (type === "success" || type === "warning" || type === "error") {
      tg.HapticFeedback.notificationOccurred(type);
    } else {
      tg.HapticFeedback.impactOccurred(type);
    }
  };

  return { tg, adminId, expand, close, ready, triggerHaptic };
}
