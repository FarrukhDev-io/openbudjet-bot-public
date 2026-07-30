import React from "react";
import { FiClock, FiCheckSquare, FiSlash } from "react-icons/fi";

type Tab = "pending" | "paid" | "rejected";

interface TabNavigationProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
  pendingCount: number;
}

export const TabNavigation: React.FC<TabNavigationProps> = ({
  activeTab,
  onTabChange,
  pendingCount,
}) => {
  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    {
      id: "pending",
      label: `Kutayotganlar (${pendingCount})`,
      icon: <FiClock className="text-sm" />,
    },
    {
      id: "paid",
      label: "To'langanlar",
      icon: <FiCheckSquare className="text-sm" />,
    },
    {
      id: "rejected",
      label: "Rad etilganlar",
      icon: <FiSlash className="text-sm" />,
    },
  ];

  return (
    <div className="flex bg-slate-900 border border-slate-800 rounded-xl p-1.5 gap-1 mb-4">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-1 text-[11px] font-bold rounded-lg transition-all duration-200 ${
            activeTab === tab.id
              ? "bg-slate-800 text-slate-100 shadow-sm"
              : "text-slate-400 hover:text-slate-200 bg-transparent"
          }`}
        >
          {tab.icon}
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
};
