import React, { useState, useEffect } from "react";
import { FiCheck, FiX } from "react-icons/fi";
import { Modal } from "./ui/Modal";

interface RejectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (note: string) => void;
  submitting: boolean;
  title: string;
}

export const RejectModal: React.FC<RejectModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  submitting,
  title
}) => {
  const [rejectNote, setRejectNote] = useState("");

  useEffect(() => {
    if (!isOpen) {
      setRejectNote("");
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <h2 className="text-base font-extrabold text-slate-100 mb-4">{title}</h2>
      <textarea
        placeholder="Sababini yozing..."
        value={rejectNote}
        onChange={(e) => setRejectNote(e.target.value)}
        rows={4}
        className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:border-rose-500 focus:outline-none transition-all resize-none mb-4"
      />
      <div className="flex gap-3">
        <button
          disabled={submitting || !rejectNote.trim()}
          onClick={() => onSubmit(rejectNote)}
          className="flex-1 py-2.5 bg-rose-500 hover:bg-rose-600 active:scale-[0.98] transition-all text-white font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
        >
          <FiCheck className="text-sm" /> Tasdiqlash
        </button>
        <button
          onClick={onClose}
          className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 active:scale-[0.98] transition-all text-slate-100 font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 cursor-pointer"
        >
          <FiX className="text-sm" /> Bekor qilish
        </button>
      </div>
    </Modal>
  );
};
