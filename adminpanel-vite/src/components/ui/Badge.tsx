import React from "react";

type BadgeStatus = "pending" | "paid" | "rejected";

interface BadgeProps {
  status: BadgeStatus;
}

const config: Record<BadgeStatus, { label: string; classes: string; emoji: string }> = {
  pending: {
    emoji: "⏳",
    label: "Kutilmoqda",
    classes: "bg-amber-500/15 text-amber-400 border border-amber-500/30",
  },
  paid: {
    emoji: "✅",
    label: "To'langan",
    classes: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
  },
  rejected: {
    emoji: "❌",
    label: "Rad etildi",
    classes: "bg-rose-500/15 text-rose-400 border border-rose-500/30",
  },
};

export const Badge: React.FC<BadgeProps> = ({ status }) => {
  const { emoji, label, classes } = config[status];
  return (
    <span
      className={[
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold",
        classes,
      ].join(" ")}
    >
      <span>{emoji}</span>
      {label}
    </span>
  );
};
