import React from "react";

interface CardProps {
  status?: "pending" | "paid" | "rejected" | "default";
  className?: string;
  children: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
  status = "default",
  className = "",
  children
}) => {
  const getBorderClasses = () => {
    switch (status) {
      case "pending":
        return "border-l-4 border-l-amber-500 border-y border-r border-slate-800/60 rounded-r-2xl";
      case "paid":
        return "border-l-4 border-l-emerald-500 border-y border-r border-slate-800/60 rounded-r-2xl";
      case "rejected":
        return "border-l-4 border-l-rose-500 border-y border-r border-slate-800/60 rounded-r-2xl";
      case "default":
      default:
        return "border border-slate-800/60 rounded-2xl";
    }
  };

  return (
    <div className={`bg-slate-900 p-4 flex flex-col gap-3 ${getBorderClasses()} ${className}`}>
      {children}
    </div>
  );
};
