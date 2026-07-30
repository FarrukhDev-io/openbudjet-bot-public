import React from "react";
import type { Stats } from "../types";
import { Card } from "./ui/Card";
import {
  FiUsers,
  FiBarChart2,
  FiCheckCircle,
  FiCalendar,
  FiClock,
  FiDollarSign,
  FiUserCheck,
  FiTrendingUp,
} from "react-icons/fi";

interface StatsGridProps {
  stats: Stats | null;
  loading: boolean;
}

type StatKey = keyof Omit<Stats, "total_paid_sum">;

const statItems: {
  key: StatKey;
  icon: React.ReactNode;
  label: string;
  color: string;
  iconColor: string;
}[] = [
  {
    key: "total_users",
    icon: <FiUsers />,
    label: "Foydalanuvchilar",
    color: "text-slate-100",
    iconColor: "text-slate-400",
  },
  {
    key: "total_votes",
    icon: <FiBarChart2 />,
    label: "Ovozlar",
    color: "text-slate-100",
    iconColor: "text-slate-400",
  },
  {
    key: "confirmed",
    icon: <FiCheckCircle />,
    label: "Tasdiqlangan",
    color: "text-emerald-400",
    iconColor: "text-emerald-500",
  },
  {
    key: "today_votes",
    icon: <FiCalendar />,
    label: "Bugun",
    color: "text-sky-400",
    iconColor: "text-sky-500",
  },
  {
    key: "pending_pays",
    icon: <FiClock />,
    label: "Kutilmoqda",
    color: "text-amber-400",
    iconColor: "text-amber-500",
  },
  {
    key: "paid_count",
    icon: <FiDollarSign />,
    label: "To'langan",
    color: "text-emerald-400",
    iconColor: "text-emerald-500",
  },
  {
    key: "total_refs",
    icon: <FiUserCheck />,
    label: "Referrallar",
    color: "text-indigo-400",
    iconColor: "text-indigo-400",
  },
];

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
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="grid grid-cols-2 gap-3 mb-4">
      {statItems.map(({ key, icon, label, color, iconColor }) => (
        <Card key={key} className="flex flex-col justify-between min-h-[90px]">
          <div className="flex justify-between items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 leading-tight">
              {label}
            </span>
            <span className={`text-base ${iconColor}`}>{icon}</span>
          </div>
          <span className={`text-2xl font-black mt-2 ${color}`}>
            {(stats[key] as number).toLocaleString()}
          </span>
        </Card>
      ))}

      {/* Wide total paid sum card */}
      <Card className="col-span-2 flex flex-col justify-between min-h-[90px]">
        <div className="flex justify-between items-start">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Jami summa
          </span>
          <FiTrendingUp className="text-base text-indigo-400" />
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
