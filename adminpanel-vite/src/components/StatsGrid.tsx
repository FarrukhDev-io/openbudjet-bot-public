import React from "react";
import type { Stats } from "../types";
import { Card } from "./ui/Card";

interface StatsGridProps {
  stats: Stats | null;
  loading: boolean;
}

const statItems = [
  { key: "total_users",    emoji: "👥", label: "Foydalanuvchilar",  color: "text-slate-100" },
  { key: "total_votes",    emoji: "🗳",  label: "Ovozlar",           color: "text-slate-100" },
  { key: "confirmed",      emoji: "✅", label: "Tasdiqlangan",      color: "text-emerald-400" },
  { key: "today_votes",    emoji: "📅", label: "Bugun",             color: "text-sky-400" },
  { key: "pending_pays",   emoji: "⏳", label: "Kutilmoqda",        color: "text-amber-400" },
  { key: "paid_count",     emoji: "💰", label: "To'langan",         color: "text-emerald-400" },
  { key: "total_refs",     emoji: "👤", label: "Referrallar",       color: "text-indigo-400" },
] as const;

function SkeletonCard() {
  return (
    <Card className="flex flex-col justify-between min-h-[90px] animate-pulse">
      <div className="h-3 bg-slate-700 rounded w-3/4 mb-4" />
      <div className="h-7 bg-slate-700 rounded w-1/2" />
    </Card>
  );
}

export const StatsGrid: React.FC<StatsGridProps> = React.memo(({ stats, loading }) => {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3 mb-4">
        {Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)}
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="grid grid-cols-2 gap-3 mb-4">
      {statItems.map(({ key, emoji, label, color }) => (
        <Card key={key} className="flex flex-col justify-between min-h-[90px]">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 leading-tight">{label}</span>
            <span className="text-base">{emoji}</span>
          </div>
          <span className={`text-2xl font-black mt-2 ${color}`}>
            {(stats[key] as number).toLocaleString()}
          </span>
        </Card>
      ))}

      {/* Wide total paid sum card */}
      <Card className="col-span-2 flex flex-col justify-between min-h-[90px]">
        <div className="flex justify-between items-start">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Jami summa</span>
          <span className="text-base">💵</span>
        </div>
        <span className="text-2xl font-black mt-2 text-indigo-400">
          {stats.total_paid_sum.toLocaleString()}{" "}
          <span className="text-sm font-normal text-slate-400">so'm</span>
        </span>
      </Card>
    </div>
  );
});

StatsGrid.displayName = "StatsGrid";
