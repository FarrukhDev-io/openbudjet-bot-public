import React from "react";

interface ButtonProps {
  children: React.ReactNode;
  onClick?: (e?: React.MouseEvent<HTMLButtonElement>) => void;
  variant?: "primary" | "danger" | "ghost" | "success" | "secondary";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  loading?: boolean;
  className?: string;
  /** Custom click handler for internal confirm-flow support */
  onConfirmClick?: (e?: React.MouseEvent<HTMLButtonElement>) => void;
}

const variantClasses: Record<string, string> = {
  primary: "bg-indigo-600 hover:bg-indigo-500 text-white",
  success: "bg-emerald-600 hover:bg-emerald-500 text-white",
  danger: "bg-rose-600 hover:bg-rose-500 text-white",
  ghost: "bg-transparent hover:bg-white/5 text-slate-300 border border-slate-700",
  secondary: "bg-slate-800 hover:bg-slate-700 text-slate-100",
};

const sizeClasses: Record<string, string> = {
  sm: "px-3 py-1.5 text-[11px] rounded-lg",
  md: "px-4 py-2.5 text-xs rounded-xl",
  lg: "px-5 py-3 text-sm rounded-2xl",
};

export const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  onConfirmClick,
  variant = "secondary",
  size = "md",
  disabled = false,
  loading = false,
  className = "",
}) => {
  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    if (loading || disabled) return;
    const cb = onConfirmClick ?? onClick;
    cb?.(e);
  };

  return (
    <button
      onClick={handleClick}
      disabled={disabled || loading}
      className={[
        "font-bold transition-all active:scale-[0.98] disabled:opacity-50",
        "flex items-center justify-center gap-1.5 cursor-pointer",
        variantClasses[variant] ?? variantClasses.secondary,
        sizeClasses[size] ?? sizeClasses.md,
        className,
      ].join(" ")}
    >
      {loading ? (
        <span className="flex items-center gap-1.5">
          <svg className="animate-spin h-3.5 w-3.5 text-current" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Yuklanmoqda...
        </span>
      ) : (
        children
      )}
    </button>
  );
};
