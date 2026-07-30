import React, { useState, useEffect } from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "success" | "danger" | "secondary";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  needConfirm?: boolean;
  confirmText?: string;
  onConfirmClick?: (e?: any) => void;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = "secondary",
  size = "md",
  loading = false,
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
    if (loading) return;
    const callback = onConfirmClick || props.onClick;
    if (needConfirm) {
      if (isArmed) {
        if (callback) (callback as any)(e);
        setIsArmed(false);
      } else {
        setIsArmed(true);
      }
    } else {
      if (callback) (callback as any)(e);
    }
  };

  const getVariantClasses = () => {
    if (isArmed) {
      return "bg-amber-500 hover:bg-amber-600 text-white animate-pulse";
    }
    switch (variant) {
      case "primary":
        return "bg-indigo-600 hover:bg-indigo-700 text-white";
      case "success":
        return "bg-emerald-500 hover:bg-emerald-600 text-white";
      case "danger":
        return "bg-rose-500 hover:bg-rose-600 text-white";
      case "secondary":
      default:
        return "bg-slate-800 hover:bg-slate-700 text-slate-100";
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case "sm":
        return "px-3 py-1.5 text-[11px] rounded-lg";
      case "lg":
        return "px-5 py-3 text-sm rounded-2xl";
      case "md":
      default:
        return "px-4 py-2.5 text-xs rounded-xl";
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={loading || props.disabled}
      className={`font-bold transition-all active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-1.5 cursor-pointer ${getVariantClasses()} ${getSizeClasses()} ${className}`}
      {...props}
    >
      {loading ? (
        <span className="flex items-center gap-1">
          <svg className="animate-spin h-3.5 w-3.5 text-current" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Yuklanmoqda...
        </span>
      ) : isArmed ? (
        confirmText
      ) : (
        children
      )}
    </button>
  );
};
