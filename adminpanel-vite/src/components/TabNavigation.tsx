import React from "react";
import type { TabType } from "../types";

interface TabNavigationProps {
  activeTab: TabType;
  onChange: (tab: TabType) => void;
  pendingCount: number;
}

type TabConfig = { id: TabType; label: string; emoji: string };

const tabs: TabConfig[] = [
  { id: "stats",    emoji: "📊", label: "Statistika" },
  { id: "pending",  emoji: "⏳", label: "Kutilmoqda" },
  { id: "paid",     emoji: "✅", label: "To'langan" },
  { id: "rejected", emoji: "❌", label: "Rad etilgan" },
];

export const TabNavigation: React.FC<TabNavigationProps> = ({
  activeTab,
  onChange,
  pendingCount,
}) => (
  <div className="flex bg-slate-900/80 border border-slate-800 rounded-2xl p-1.5 gap-1 mb-4">
    {tabs.map((tab) => {
      const isActive = activeTab === tab.id;
      const label =
        tab.id === "pending" && pendingCount > 0
          ? `${tab.label} (${pendingCount})`
          : tab.label;

      return (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={[
            "flex-1 flex flex-col items-center justify-center gap-0.5 py-2 px-1 rounded-xl",
            "text-[10px] font-bold transition-all duration-200 cursor-pointer",
            isActive
              ? "bg-slate-800 text-indigo-300 shadow-sm ring-1 ring-indigo-500/30"
              : "text-slate-500 hover:text-slate-300 hover:bg-slate-800/40",
          ].join(" ")}
        >
          <span className="text-sm">{tab.emoji}</span>
          <span className="leading-none">{label}</span>
          {isActive && (
            <span className="block w-4 h-0.5 rounded-full bg-indigo-500 mt-0.5" />
          )}
        </button>
      );
    })}
  </div>
);
