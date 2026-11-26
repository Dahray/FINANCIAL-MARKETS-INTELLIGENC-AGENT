"use client";

import React from "react";

export function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-slate-800/90 bg-slate-900/75 backdrop-blur-sm shadow-lg ${className}`}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`border-b border-slate-800/80 px-5 py-4 ${className}`}>
      {children}
    </div>
  );
}

export function CardTitle({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <h3 className={`text-sm font-semibold tracking-wide text-slate-100 uppercase ${className}`}>
      {children}
    </h3>
  );
}

export function CardContent({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}

export function Badge({
  children,
  variant = "default",
  className = "",
}: {
  children: React.ReactNode;
  variant?: "default" | "emerald" | "amber" | "rose" | "sky" | "purple";
  className?: string;
}) {
  const styles: Record<string, string> = {
    default: "bg-slate-800 text-slate-200 border-slate-700",
    emerald: "bg-emerald-950/80 text-emerald-300 border-emerald-700/60",
    amber: "bg-amber-950/80 text-amber-300 border-amber-700/60",
    rose: "bg-rose-950/80 text-rose-300 border-rose-700/60",
    sky: "bg-sky-950/80 text-sky-300 border-sky-700/60",
    purple: "bg-purple-950/80 text-purple-300 border-purple-700/60",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-medium ${styles[variant]} ${className}`}
    >
      {children}
    </span>
  );
}

export function MetricStatCard({
  label,
  value,
  subValue,
  changePct,
  unit,
  badgeText,
  invertColor = false,
}: {
  label: string;
  value: string | number;
  subValue?: string;
  changePct?: number | null;
  unit?: string;
  badgeText?: string;
  invertColor?: boolean;
}) {
  const isPositive = (changePct ?? 0) >= 0;
  const goodColor = invertColor ? !isPositive : isPositive;

  return (
    <Card className="p-4 hover:border-slate-700 transition-colors">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          {label}
        </span>
        {badgeText && <Badge variant="sky">{badgeText}</Badge>}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold font-mono text-white">{value}</span>
        {unit && <span className="text-xs text-slate-400 font-mono">{unit}</span>}
      </div>
      <div className="mt-2 flex items-center justify-between text-xs">
        {changePct !== undefined && changePct !== null ? (
          <span
            className={`font-mono font-semibold ${
              goodColor ? "text-emerald-400" : "text-rose-400"
            }`}
          >
            {changePct >= 0 ? "+" : ""}
            {changePct.toFixed(2)}%
          </span>
        ) : (
          <span className="text-slate-500">Verified Primary Data</span>
        )}
        {subValue && <span className="text-slate-400">{subValue}</span>}
      </div>
    </Card>
  );
}

export function ScoreBar({
  label,
  score,
}: {
  label: string;
  score: number;
}) {
  const pct = Math.min(100, Math.max(0, score));
  const barColor =
    pct >= 85
      ? "bg-emerald-500"
      : pct >= 70
      ? "bg-sky-500"
      : pct >= 55
      ? "bg-amber-500"
      : "bg-rose-500";

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-300">{label}</span>
        <span className="font-mono font-semibold text-slate-100">
          {pct.toFixed(1)}/100
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor} transition-all duration-300`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
