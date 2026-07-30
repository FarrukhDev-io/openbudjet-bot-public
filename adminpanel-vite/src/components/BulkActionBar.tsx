import React from "react";
import { FiCheck, FiX } from "react-icons/fi";

interface BulkActionBarProps {
  selectedCount: number;
  onBulkPay: () => void;
  onBulkReject: () => void;
  submitting: boolean;
}

export const BulkActionBar: React.FC<BulkActionBarProps> = ({
  selectedCount,
  onBulkPay,
  onBulkReject,
  submitting
}) => {
  if (selectedCount === 0) return null;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-md bg-slate-800/90 backdrop-blur-md border border-slate-700/40 rounded-2xl p-4 shadow-md flex justify-between items-center z-40 animate-in slide-in-from-bottom duration-300">
      <span className="text-xs text-slate-300 font-bold">
        <span className="text-indigo-400 font-black">{selectedCount} ta</span> tanlandi
      </span>
      <div className="flex gap-2">
        <button
          disabled={submitting}
          onClick={onBulkPay}
          className="px-3.5 py-2 bg-emerald-500 hover:bg-emerald-600 active:scale-[0.98] transition-all text-white font-extrabold text-xs rounded-xl flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
        >
          <FiCheck /> To'lash
        </button>
        <button
          disabled={submitting}
          onClick={onBulkReject}
          className="px-3.5 py-2 bg-rose-500 hover:bg-rose-600 active:scale-[0.98] transition-all text-white font-extrabold text-xs rounded-xl flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
        >
          <FiX /> Rad etish
        </button>
      </div>
    </div>
  );
};
