import React from "react";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  status?: "pending" | "paid" | "rejected" | "none";
  className?: string;
}

const statusAccent: Record<string, string> = {
  none: "",
  pending: "border-l-4 border-l-amber-500",
  paid: "border-l-4 border-l-emerald-500",
  rejected: "border-l-4 border-l-rose-500",
};

export const Card: React.FC<CardProps> = ({
  children,
  status = "none",
  className = "",
  ...props
}) => (
  <div
    className={[
      "bg-slate-900 border border-slate-800/80 rounded-2xl p-4 shadow-md",
      "transition-all duration-200",
      statusAccent[status] ?? "",
      className,
    ].join(" ")}
    {...props}
  >
    {children}
  </div>
);
