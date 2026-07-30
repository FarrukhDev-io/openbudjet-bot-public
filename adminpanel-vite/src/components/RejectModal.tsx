import React, { useState, useEffect } from "react";
import { FiCheck, FiX } from "react-icons/fi";

interface RejectModalProps {
  isOpen: boolean;
  paymentId: number | null;
  onConfirm: (id: number, note: string) => void;
  onClose: () => void;
}

export const RejectModal: React.FC<RejectModalProps> = ({
  isOpen,
  paymentId,
  onConfirm,
  onClose,
}) => {
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isOpen) {
      setNote("");
      setError("");
    }
  }, [isOpen]);

  if (!isOpen || paymentId === null) return null;

  const handleConfirm = () => {
    if (!note.trim() || note.trim().length < 3) {
      setError("Sabab kamida 3 ta belgidan iborat bo'lishi kerak.");
      return;
    }
    onConfirm(paymentId, note.trim());
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Dialog — L3 elevation */}
      <div
        className="relative z-10 w-full max-w-md bg-slate-800 border border-slate-700 shadow-2xl rounded-t-3xl sm:rounded-3xl p-6 mx-0 sm:mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-extrabold text-slate-100 mb-1">❌ Rad etish sababi</h2>
        <p className="text-xs text-slate-400 mb-4">Foydalanuvchiga yuboriladi</p>

        <textarea
          autoFocus
          placeholder="Sababini yozing (kamida 3 ta belgi)..."
          value={note}
          onChange={(e) => {
            setNote(e.target.value);
            setError("");
          }}
          rows={4}
          className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-xl text-slate-100 text-sm
            focus:border-rose-500 focus:outline-none transition-all resize-none"
        />

        {error && (
          <p className="text-rose-400 text-xs mt-1.5">{error}</p>
        )}

        <div className="flex gap-3 mt-4">
          <button
            onClick={handleConfirm}
            className="flex-1 py-2.5 bg-rose-600 hover:bg-rose-500 active:scale-[0.98] transition-all
              text-white font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <FiCheck /> Rad etish
          </button>
          <button
            onClick={onClose}
            className="flex-1 py-2.5 bg-slate-700 hover:bg-slate-600 active:scale-[0.98] transition-all
              text-slate-100 font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <FiX /> Bekor qilish
          </button>
        </div>
      </div>
    </div>
  );
};
