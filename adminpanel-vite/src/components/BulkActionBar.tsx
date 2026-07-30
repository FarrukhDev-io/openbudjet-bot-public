import React from "react";
import { Button } from "./ui/Button";
import { FiCheckSquare, FiTrash2 } from "react-icons/fi";

interface BulkActionBarProps {
  selectedCount: number;
  onBulkApprove: () => void;
  onBulkReject: () => void;
  submitting: boolean;
}

export const BulkActionBar: React.FC<BulkActionBarProps> = ({
  selectedCount,
  onBulkApprove,
  onBulkReject,
  submitting,
}) => {
  if (selectedCount === 0) return null;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 w-11/12 max-w-[500px] bg-slate-900/95 border border-slate-800 rounded-2xl p-3.5 shadow-2xl flex items-center justify-between z-40 backdrop-blur-md animate-in slide-in-from-bottom-6 duration-200">
      <div className="flex flex-col">
        <span className="text-xs text-slate-400 font-bold uppercase tracking-wide">
          Guruhli boshqaruv
        </span>
        <span className="text-sm font-extrabold text-slate-100">{selectedCount} ta tanlandi</span>
      </div>

      <div className="flex gap-2">
        <Button
          variant="success"
          size="sm"
          disabled={submitting}
          onClick={onBulkApprove}
          className="h-10 text-xs px-3.5 font-bold"
        >
          <FiCheckSquare className="text-sm" />
          <span>To'lash</span>
        </Button>
        <Button
          variant="danger"
          size="sm"
          disabled={submitting}
          onClick={onBulkReject}
          className="h-10 text-xs px-3.5 font-bold"
        >
          <FiTrash2 className="text-sm" />
          <span>Rad etish</span>
        </Button>
      </div>
    </div>
  );
};
