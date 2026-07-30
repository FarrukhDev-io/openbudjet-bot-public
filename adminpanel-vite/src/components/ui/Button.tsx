import React, { useState, useEffect } from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "success" | "danger" | "secondary";
  needConfirm?: boolean;
  confirmText?: string;
  onConfirmClick: () => void;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = "secondary",
  needConfirm = false,
  confirmText = "Aniqmi? 🤨",
  onConfirmClick,
  className = "",
  children,
  ...props
}) => {
  const [isArmed, setIsArmed] = useState(false);

  useEffect(() => {
    if (!isArmed) return;
    const timer = setTimeout(() => {
      setIsArmed(false);
    }, 3000);
    return () => clearTimeout(timer);
  }, [isArmed]);

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    if (needConfirm) {
      if (isArmed) {
        onConfirmClick();
        setIsArmed(false);
      } else {
        setIsArmed(true);
      }
    } else {
      onConfirmClick();
    }
  };

  const getVariantClasses = () => {
    if (isArmed) {
      return "bg-amber-500 hover:bg-amber-600 text-white animate-pulse";
    }
    switch (variant) {
      case "success":
        return "bg-emerald-500 hover:bg-emerald-600 text-white";
      case "danger":
        return "bg-rose-500 hover:bg-rose-600 text-white";
      case "secondary":
      default:
        return "bg-slate-800 hover:bg-slate-700 text-slate-100";
    }
  };

  return (
    <button
      onClick={handleClick}
      className={`px-4 py-2.5 rounded-xl font-bold text-xs transition-all active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-1.5 ${getVariantClasses()} ${className}`}
      {...props}
    >
      {isArmed ? confirmText : children}
    </button>
  );
};
