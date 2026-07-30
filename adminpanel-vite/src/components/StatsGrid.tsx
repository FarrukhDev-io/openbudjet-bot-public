import React from "react";
import type { Stats } from "../types";
import { Card } from "./ui/Card";
import { FiUsers, FiCheckCircle, FiClock, FiCheck, FiDollarSign } from "react-icons/fi";

interface StatsGridProps {
  stats: Stats | null;
}

export const StatsGrid: React.FC<StatsGridProps> = React.memo(({ stats }) => {
  if (!stats) return null;

  return (
    <div className="grid grid-cols-2 gap-3 mb-6">
      <Card className="flex flex-col justify-between min-h-[90px]">
        <div className="flex justify-between items-center text-slate-400">
          <span className="text-[11px] font-bold uppercase tracking-wider">Jami a'zolar</span>
          <FiUsers className="text-slate-400 text-sm" />
        </div>
        <span className="text-xl font-extrabold text-slate-100">{stats.total_users}</span>
      </Card>

      <Card className="flex flex-col justify-between min-h-[90px]">
        <div className="flex justify-between items-center text-slate-400">
          <span className="text-[11px] font-bold uppercase tracking-wider">Ovozlar (Tasdiq)</span>
          <FiCheckCircle className="text-slate-400 text-sm" />
        </div>
        <span className="text-xl font-extrabold text-slate-100">
          {stats.total_votes} <span className="text-xs font-normal text-slate-400">({stats.confirmed})</span>
        </span>
      </Card>

      <Card className="flex flex-col justify-between min-h-[90px]">
        <div className="flex justify-between items-center text-slate-400">
          <span className="text-[11px] font-bold uppercase tracking-wider">Bugungi ovozlar</span>
          <FiCheck className="text-emerald-400 text-sm" />
        </div>
        <span className="text-xl font-extrabold text-emerald-400">{stats.today_votes}</span>
      </Card>

      <Card className="flex flex-col justify-between min-h-[90px] border-l-amber-500/80 border-l-2">
        <div className="flex justify-between items-center text-slate-400">
          <span className="text-[11px] font-bold uppercase tracking-wider">Kutayotgan to'lovlar</span>
          <FiClock className="text-amber-500 text-sm" />
        </div>
        <span className="text-xl font-extrabold text-amber-500">{stats.pending_pays}</span>
      </Card>

      <Card className="col-span-2 flex flex-col justify-between min-h-[90px]">
        <div className="flex justify-between items-center text-slate-400">
          <span className="text-[11px] font-bold uppercase tracking-wider">Jami to'langan summa</span>
          <FiDollarSign className="text-indigo-400 text-sm" />
        </div>
        <span className="text-2xl font-black text-indigo-400">
          {stats.total_paid_sum.toLocaleString()} <span className="text-sm font-normal text-slate-400">so'm</span>
        </span>
      </Card>
    </div>
  );
});

StatsGrid.displayName = "StatsGrid";
