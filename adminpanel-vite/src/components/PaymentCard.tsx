import React from "react";
import { FiCopy, FiCheck, FiX } from "react-icons/fi";
import type { PaymentRequest } from "../types";
import { Card } from "./ui/Card";
import { Button } from "./ui/Button";

interface PaymentCardProps {
  payment: PaymentRequest;
  activeTab: "pending" | "paid" | "rejected";
  isSelected: boolean;
  onSelectChange: (id: number, checked: boolean) => void;
  copiedId: number | null;
  onCopyClick: (text: string, id: number) => void;
  onPayClick: (id: number) => void;
  onRejectClick: (id: number) => void;
}

export const PaymentCard: React.FC<PaymentCardProps> = React.memo(({
  payment,
  activeTab,
  isSelected,
  onSelectChange,
  copiedId,
  onCopyClick,
  onPayClick,
  onRejectClick
}) => {
  const formatCard = (card: string) => {
    const cleaned = card.replace(/\s+/g, "");
    const parts = [];
    for (let i = 0; i < cleaned.length; i += 4) {
      parts.push(cleaned.substring(i, i + 4));
    }
    return parts.join(" ");
  };

  return (
    <Card status={payment.status as any}>
      <div className="flex justify-between items-start">
        <div className="flex gap-3 items-center">
          {activeTab === "pending" && (
            <input
              type="checkbox"
              checked={isSelected}
              onChange={(e) => onSelectChange(payment.id, e.target.checked)}
              className="w-4 h-4 rounded border-slate-800 text-indigo-600 focus:ring-indigo-500 accent-indigo-500 cursor-pointer"
            />
          )}
          <div>
            <h3 className="font-bold text-sm text-slate-200">{payment.full_name}</h3>
            {payment.username && <span className="text-xs text-indigo-400 font-semibold">@{payment.username}</span>}
          </div>
        </div>
        <span className="font-black text-sm text-emerald-400">{payment.amount.toLocaleString()} so'm</span>
      </div>

      <div className="text-xs text-slate-300 flex flex-col gap-2">
        <p>
          <strong className="text-slate-500">Tel:</strong> +{payment.phone}
        </p>
        <div className="flex justify-between items-center bg-slate-950/50 border border-slate-800/80 px-3 py-2 rounded-xl">
          <code className="font-mono text-sm text-slate-200 font-bold tracking-wider">
            {formatCard(payment.card_number)}
          </code>
          <button
            onClick={() => onCopyClick(payment.card_number, payment.id)}
            className="px-2.5 py-1 bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 hover:text-slate-100 rounded-lg text-[10px] font-bold flex items-center gap-1 active:scale-95 transition-all cursor-pointer"
          >
            {copiedId === payment.id ? "✓ Nusxalandi!" : <><FiCopy /> Nusxa</>}
          </button>
        </div>

        {/* Quick Bank Launcher */}
        {copiedId === payment.id && (
          <div className="bg-indigo-950/20 border border-indigo-900/30 p-2.5 rounded-xl mt-1 flex flex-col gap-2">
            <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
              Bank ilovasida ochish:
            </span>
            <div className="flex gap-2">
              <a
                href="clickuz://"
                className="flex-1 text-center py-2 bg-[#0096e2] rounded-lg text-white font-extrabold text-[11px] hover:opacity-90 transition-opacity"
              >
                Click
              </a>
              <a
                href="payme://"
                className="flex-1 text-center py-2 bg-[#12c8c4] rounded-lg text-white font-extrabold text-[11px] hover:opacity-90 transition-opacity"
              >
                Payme
              </a>
              <a
                href="uzumbank://"
                className="flex-1 text-center py-2 bg-[#7000ff] rounded-lg text-white font-extrabold text-[11px] hover:opacity-90 transition-opacity"
              >
                Uzum
              </a>
            </div>
          </div>
        )}

        <p className="text-[10px] text-slate-500 text-right mt-1">
          {payment.requested_at.substring(0, 16)}
        </p>
      </div>

      {activeTab === "pending" && (
        <div className="flex gap-3 mt-1">
          <Button
            variant="success"
            needConfirm
            onConfirmClick={() => onPayClick(payment.id)}
            className="flex-1"
          >
            <FiCheck className="text-sm" /> To'landi
          </Button>
          <Button
            variant="danger"
            needConfirm
            onConfirmClick={() => onRejectClick(payment.id)}
            className="flex-1"
          >
            <FiX className="text-sm" /> Rad etish
          </Button>
        </div>
      )}
    </Card>
  );
});

PaymentCard.displayName = "PaymentCard";
