import React, { useState } from "react";
import type { Payment } from "../types";
import { Card } from "./ui/Card";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import { FiCopy, FiCheck, FiX, FiExternalLink } from "react-icons/fi";

interface PaymentCardProps {
  payment: Payment;
  onApprove: (id: number) => void;
  onReject: (id: number, note: string) => void;
  disabled?: boolean;
  /** Show selection checkbox (used in pending bulk mode) */
  isSelected?: boolean;
  onSelect?: (id: number, checked: boolean) => void;
  /** Open the reject modal instead of inline reject */
  onRejectPrompt?: (id: number) => void;
  activeTab?: string;
  onCopy?: (text: string) => void;
}

function maskCard(card: string) {
  const d = card.replace(/\s+/g, "");
  if (d.length >= 8) return `${d.slice(0, 4)} **** **** ${d.slice(-4)}`;
  return card;
}

function formatCard(card: string) {
  const clean = card.replace(/\s+/g, "");
  return clean.match(/.{1,4}/g)?.join(" ") ?? card;
}

const bankApps = (card: string, amount: number) => [
  { name: "Click",    url: `https://my.click.uz/services/p2p?card_number=${card}&amount=${amount}` },
  { name: "Payme",   url: `https://checkout.paycom.uz/card-to-card?to=${card}&amount=${amount * 100}` },
  { name: "Uzum",    url: `https://uzumbank.uz/transfer?card=${card}&amount=${amount}` },
];

export const PaymentCard: React.FC<PaymentCardProps> = React.memo(({
  payment,
  onApprove,
  onReject,
  onRejectPrompt,
  disabled = false,
  isSelected = false,
  onSelect,
  activeTab,
  onCopy,
}) => {
  const [approveArmed, setApproveArmed] = useState(false);
  const [rejectArmed, setRejectArmed] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(payment.card_number);
    setCopied(true);
    onCopy?.(payment.card_number);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleApproveClick = () => {
    if (approveArmed) {
      onApprove(payment.id);
      setApproveArmed(false);
    } else {
      setApproveArmed(true);
      setRejectArmed(false);
      setTimeout(() => setApproveArmed(false), 3000);
    }
  };

  const handleRejectClick = () => {
    if (rejectArmed) {
      if (onRejectPrompt) {
        onRejectPrompt(payment.id);
      } else {
        onReject(payment.id, "");
      }
      setRejectArmed(false);
    } else {
      setRejectArmed(true);
      setApproveArmed(false);
      setTimeout(() => setRejectArmed(false), 3000);
    }
  };

  const isPending = payment.status === "pending";

  return (
    <Card status={payment.status as any} className="flex flex-col gap-3 select-none">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-2.5">
          {activeTab === "pending" && onSelect && (
            <input
              type="checkbox"
              checked={isSelected}
              onChange={(e) => onSelect(payment.id, e.target.checked)}
              className="w-5 h-5 rounded-md accent-indigo-600 cursor-pointer"
            />
          )}
          <div>
            <h3 className="text-sm font-bold text-slate-100 leading-tight">{payment.full_name}</h3>
            {payment.username && (
              <span className="text-xs text-indigo-400 font-semibold">@{payment.username}</span>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <Badge status={payment.status} />
          <span className="text-sm font-extrabold text-emerald-400">
            {payment.amount.toLocaleString()} so'm
          </span>
        </div>
      </div>

      {/* Details */}
      <div className="text-xs text-slate-400 flex flex-col gap-1.5">
        <p><strong className="text-slate-300">🆔 TG ID:</strong>{" "}
          <code className="font-mono text-indigo-300 bg-slate-800/60 px-1 py-0.5 rounded">{payment.tg_id}</code>
        </p>
        <p><strong className="text-slate-300">📞 Tel:</strong> +{payment.phone}</p>

        {/* Card row */}
        <div className="flex justify-between items-center bg-slate-950/60 border border-slate-800/40 px-3 py-2 rounded-xl mt-1">
          <code className="text-slate-100 font-mono text-sm tracking-wider">{formatCard(payment.card_number)}</code>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-[10px] font-semibold text-slate-300 rounded-lg border border-slate-700/40 transition-colors cursor-pointer"
          >
            {copied ? <><FiCheck className="text-emerald-400" /><span className="text-emerald-400">Nusxalandi</span></> : <><FiCopy /><span>Nusxa</span></>}
          </button>
        </div>

        {/* Masked card hint */}
        <p className="text-[10px] text-slate-500">{maskCard(payment.card_number)}</p>

        {/* Bank deep links (pending only) */}
        {isPending && (
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[10px] text-slate-500">Ilovani ochish:</span>
            <div className="flex gap-1.5">
              {bankApps(payment.card_number, payment.amount).map((app) => (
                <a
                  key={app.name}
                  href={app.url}
                  target="_blank"
                  rel="noreferrer"
                  className="px-2 py-1 bg-slate-800 hover:bg-indigo-600/20 text-[10px] font-semibold text-indigo-400 rounded-md flex items-center gap-1 border border-slate-700/40 transition-colors"
                >
                  {app.name} <FiExternalLink className="text-[8px]" />
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Date and rejection note */}
        <div className="flex justify-between items-center text-[10px] text-slate-500 mt-1">
          <span>{payment.requested_at?.substring(0, 16)}</span>
          {payment.processed_at && (
            <span className="text-slate-600">→ {payment.processed_at?.substring(0, 16)}</span>
          )}
        </div>

        {payment.status === "rejected" && payment.admin_note && (
          <div className="mt-1 px-3 py-2 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-[11px] italic">
            📝 {payment.admin_note}
          </div>
        )}
      </div>

      {/* Action buttons */}
      {isPending && (
        <div className="flex gap-2.5 mt-1">
          <Button
            variant={approveArmed ? "ghost" : "success"}
            className="flex-1 text-xs"
            onClick={handleApproveClick}
            disabled={disabled}
          >
            <FiCheck />
            <span>{approveArmed ? "Aniqmi? ✅" : "Tasdiqlash"}</span>
          </Button>
          <Button
            variant={rejectArmed ? "ghost" : "danger"}
            className="flex-1 text-xs"
            onClick={handleRejectClick}
            disabled={disabled}
          >
            <FiX />
            <span>{rejectArmed ? "Aniqmi? ❌" : "Rad etish"}</span>
          </Button>
        </div>
      )}
    </Card>
  );
});

PaymentCard.displayName = "PaymentCard";
