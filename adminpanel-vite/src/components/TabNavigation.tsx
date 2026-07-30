import React from "react";
import { FiAlertCircle, FiCheckSquare, FiSlash } from "react-icons/fi";

interface TabNavigationProps {
  activeTab: "pending" | "paid" | "rejected";
  setActiveTab: (tab: "pending" | "paid" | "rejected") => void;
  pendingCount: number;
}

export const TabNavigation: React.FC<TabNavigationProps> = ({
  activeTab,
  setActiveTab,
  pendingCount
}) => {
  return (
    <div className="flex bg-slate-900 border border-slate-800 rounded-xl p-1 gap-1 mb-3">
      <button
        className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
          activeTab === "pending" ? "bg-slate-800 text-slate-100" : "text-slate-400 hover:text-slate-200"
        }`}
        onClick={() => setActiveTab("pending")}
      >
        <FiAlertCircle className="text-sm" />
        Kutilmoqda ({pendingCount})
      </button>
      <button
        className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
          activeTab === "paid" ? "bg-slate-800 text-slate-100" : "text-slate-400 hover:text-slate-200"
        }`}
        onClick={() => setActiveTab("paid")}
      >
        <FiCheckSquare className="text-sm" />
        To'langan
      </button>
      <button
        className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
          activeTab === "rejected" ? "bg-slate-800 text-slate-100" : "text-slate-400 hover:text-slate-200"
        }`}
        onClick={() => setActiveTab("rejected")}
      >
        <FiSlash className="text-sm" />
        Rad etilgan
      </button>
    </div>
  );
};
