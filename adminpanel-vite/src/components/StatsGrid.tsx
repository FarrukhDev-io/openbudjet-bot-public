import React from "react";
import { FiUsers, FiCheckCircle, FiClock, FiDollarSign } from "react-icons/fi";
import type { Stats } from "../types";

interface StatsGridProps {
  stats: Stats;
}

export const StatsGrid: React.FC<StatsGridProps> = React.memo(({ stats }) => {
  return (
    <div className="grid grid-cols-2 gap-3 mb-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-3 flex flex-col justify-center">
        <div className="flex justify-between items-center mb-1">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">A'zolar</span>
          <FiUsers className="text-indigo-400 text-sm" />
        </div>
        <span className="text-lg font-black">{stats.total_users}</span>
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-3 flex flex-col justify-center">
        <div className="flex justify-between items-center mb-1">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Ovoz (Tasdiq)</span>
          <FiCheckCircle className="text-purple-400 text-sm" />
        </div>
        <span className="text-lg font-black">
          {stats.total_votes} <span className="text-xs text-slate-400">({stats.confirmed})</span>
        </span>
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-3 flex flex-col justify-center">
        <div className="flex justify-between items-center mb-1">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Bugun</span>
          <FiCheckCircle className="text-emerald-400 text-sm" />
        </div>
        <span className="text-lg font-black text-emerald-400">{stats.today_votes}</span>
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-3 flex flex-col justify-center">
        <div className="flex justify-between items-center mb-1">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Kutilmoqda</span>
          <FiClock className="text-amber-500 text-sm" />
        </div>
        <span className="text-lg font-black text-amber-500">{stats.pending_pays}</span>
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-3 flex flex-col justify-center col-span-2">
        <div className="flex justify-between items-center mb-1">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">To'landi</span>
          <FiDollarSign className="text-indigo-400 text-sm" />
        </div>
        <span className="text-lg font-black text-indigo-400">
          {stats.total_paid_sum.toLocaleString()} so'm
        </span>
      </div>
    </div>
  );
});

StatsGrid.displayName = "StatsGrid";
