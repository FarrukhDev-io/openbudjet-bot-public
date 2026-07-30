import React, { useState, useEffect } from "react";
import type { PaymentRequest } from "../types";
import { Card } from "./ui/Card";
import { Button } from "./ui/Button";
import { FiCopy, FiCheck, FiX, FiExternalLink } from "react-icons/fi";

interface PaymentCardProps {
  payment: PaymentRequest;
  activeTab: "pending" | "paid" | "rejected";
  isSelected: boolean;
  onSelect: (id: number, checked: boolean) => void;
  onApprove: (id: number) => Promise<void>;
  onRejectPrompt: (id: number) => void;
  onCopy: (card: string) => void;
}

export const PaymentCard: React.FC<PaymentCardProps> = React.memo(({
  payment,
  activeTab,
  isSelected,
  onSelect,
  onApprove,
  onRejectPrompt,
  onCopy,
}) => {
  const [approveConfirm, setApproveConfirm] = useState(false);
  const [rejectConfirm, setRejectConfirm] = useState(false);
  const [copiedRecently, setCopiedRecently] = useState(false);

  useEffect(() => {
    let timer: any;
    if (approveConfirm) {
      timer = setTimeout(() => setApproveConfirm(false), 3000);
    }
    return () => clearTimeout(timer);
  }, [approveConfirm]);

  useEffect(() => {
    let timer: any;
    if (rejectConfirm) {
      timer = setTimeout(() => setRejectConfirm(false), 3000);
    }
    return () => clearTimeout(timer);
  }, [rejectConfirm]);

  const handleApproveClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (approveConfirm) {
      onApprove(payment.id);
      setApproveConfirm(false);
    } else {
      setApproveConfirm(true);
      setRejectConfirm(false);
    }
  };

  const handleRejectClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (rejectConfirm) {
      onRejectPrompt(payment.id);
      setRejectConfirm(false);
    } else {
      setRejectConfirm(true);
      setApproveConfirm(false);
    }
  };

  const handleCopyClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onCopy(payment.card_number);
    setCopiedRecently(true);
    setTimeout(() => setCopiedRecently(false), 2000);
  };

  const formatCardNumber = (card: string) => {
    const clean = card.replace(/\s+/g, "");
    const chunks = [];
    for (let i = 0; i < clean.length; i += 4) {
      chunks.push(clean.substring(i, i + 4));
    }
    return chunks.join(" ");
  };

  const bankApps = [
    { name: "Click", schema: "clickuz://", url: "https://click.uz" },
    { name: "Payme", schema: "payme://", url: "https://payme.uz" },
    { name: "Uzum Bank", schema: "uzumbank://", url: "https://uzumbank.uz" },
  ];

  return (
    <Card status={activeTab} className="flex flex-col gap-3 relative select-none">
      {/* Top Header */}
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-2.5">
          {activeTab === "pending" && (
            <input
              type="checkbox"
              checked={isSelected}
              onChange={(e) => onSelect(payment.id, e.target.checked)}
              className="w-5 h-5 rounded-md accent-indigo-600 bg-slate-950 border-slate-800 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-slate-900 cursor-pointer"
            />
          )}
          <div>
            <h3 className="text-sm font-bold text-slate-100 leading-tight">
              {payment.full_name}
            </h3>
            {payment.username && (
              <span className="text-xs text-indigo-400 font-semibold">@{payment.username}</span>
            )}
          </div>
        </div>
        <span className="text-sm font-extrabold text-emerald-400">
          {payment.amount.toLocaleString()} so'm
        </span>
      </div>

      {/* Body details */}
      <div className="text-xs text-slate-400 flex flex-col gap-1.5">
        <p>
          <strong className="text-slate-300">📞 Tel:</strong> +{payment.phone}
        </p>

        {/* Card copying container */}
        <div className="flex justify-between items-center bg-slate-950/60 border border-slate-800/40 px-3 py-2 rounded-xl mt-1.5">
          <code className="text-slate-100 font-mono text-sm tracking-wider">
            {formatCardNumber(payment.card_number)}
          </code>
          <Button
            variant="secondary"
            size="sm"
            onConfirmClick={handleCopyClick}
            className="h-8 min-w-[70px]"
          >
            {copiedRecently ? (
              <span className="text-emerald-400 text-[10px]">Nusxalandi!</span>
            ) : (
              <>
                <FiCopy className="text-xs" />
                <span className="text-[10px]">Nusxa</span>
              </>
            )}
          </Button>
        </div>

        {/* Banking Deep Link Launcher - displayed when copied or pending */}
        {activeTab === "pending" && (
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] text-slate-500">Ilovani ochish:</span>
            <div className="flex gap-1.5">
              {bankApps.map((app) => (
                <a
                  key={app.name}
                  href={app.schema}
                  onClick={() => {
                    setTimeout(() => {
                      window.location.href = app.url;
                    }, 500);
                  }}
                  className="px-2 py-1 bg-slate-800 hover:bg-slate-750 text-[10px] font-semibold text-indigo-400 rounded-md flex items-center gap-1 border border-slate-700/40 transition-colors"
                >
                  {app.name} <FiExternalLink className="text-[8px]" />
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Date and Rejection note */}
        <div className="flex justify-between items-center text-[10px] text-slate-500 mt-1">
          <span>{payment.requested_at.substring(0, 16)}</span>
          {payment.status === "rejected" && payment.u_full_name && (
            <span className="text-rose-400 italic">Rad etgan: {payment.u_full_name}</span>
          )}
        </div>
      </div>

      {/* Action Buttons for Pending requests with Double Click confirm */}
      {activeTab === "pending" && (
        <div className="flex gap-2.5 mt-2">
          <Button
            variant={approveConfirm ? "danger" : "success"}
            className="flex-1 text-xs"
            onConfirmClick={handleApproveClick}
          >
            <FiCheck />
            <span>{approveConfirm ? "Aniqmi? 🤨" : "To'landi"}</span>
          </Button>
          <Button
            variant={rejectConfirm ? "primary" : "danger"}
            className="flex-1 text-xs"
            onConfirmClick={handleRejectClick}
          >
            <FiX />
            <span>{rejectConfirm ? "Aniqmi? 🤨" : "Rad etish"}</span>
          </Button>
        </div>
      )}
    </Card>
  );
});

PaymentCard.displayName = "PaymentCard";
