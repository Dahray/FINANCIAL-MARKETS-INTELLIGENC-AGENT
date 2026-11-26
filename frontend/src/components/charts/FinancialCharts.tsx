"use client";

import React, { useState } from "react";

export interface TimeseriesPoint {
  date: string;
  value: number;
  open?: number | null;
  high?: number | null;
  low?: number | null;
}

/**
 * 1. TradingView-Style Interactive Financial Market Area & Candlestick Chart
 */
export function MarketPriceChart({
  title,
  symbol,
  unit,
  data,
  sma20,
  height = 260,
}: {
  title: string;
  symbol: string;
  unit: string;
  data: TimeseriesPoint[];
  sma20?: number | null;
  height?: number;
}) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (!data || data.length < 2) {
    return (
      <div className="flex h-48 items-center justify-center text-xs text-slate-500">
        Loading verified time-series observations for {symbol}...
      </div>
    );
  }

  const values = data.map((d) => d.value);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const span = Math.max(1e-6, maxVal - minVal);
  const firstVal = values[0];
  const lastVal = values[values.length - 1];
  const isUp = lastVal >= firstVal;
  const strokeColor = isUp ? "#10b981" : "#f43f5e";
  const fillId = `grad-${symbol.replace(/[^a-zA-Z0-9]/g, "")}`;

  const width = 760;
  const padX = 16;
  const padY = 22;
  const plotW = width - padX * 2;
  const plotH = height - padY * 2;

  const toX = (i: number) => padX + (i / (data.length - 1)) * plotW;
  const toY = (v: number) => padY + plotH - ((v - minVal) / span) * plotH;

  const pointsStr = data.map((d, i) => `${toX(i).toFixed(1)},${toY(d.value).toFixed(1)}`).join(" ");
  const areaStr = `${toX(0).toFixed(1)},${(padY + plotH).toFixed(1)} ${pointsStr} ${toX(
    data.length - 1
  ).toFixed(1)},${(padY + plotH).toFixed(1)}`;

  const activePoint = hoverIdx !== null ? data[hoverIdx] : data[data.length - 1];
  const pctChange = ((lastVal / firstVal - 1) * 100).toFixed(2);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white">{title}</span>
            <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-xs text-sky-300">
              {symbol}
            </span>
          </div>
          <p className="text-xs text-slate-400">
            As of {activePoint.date} • Unit: {unit}
          </p>
        </div>
        <div className="text-right font-mono">
          <div className="text-lg font-bold text-white">
            {activePoint.value.toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </div>
          <div className={`text-xs ${isUp ? "text-emerald-400" : "text-rose-400"}`}>
            {isUp ? "+" : ""}
            {pctChange}% ({data.length} sessions)
          </div>
        </div>
      </div>

      <div className="relative w-full overflow-hidden rounded-lg border border-slate-800/90 bg-slate-950/80 p-2">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto select-none"
          onMouseLeave={() => setHoverIdx(null)}
        >
          <defs>
            <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={strokeColor} stopOpacity="0.32" />
              <stop offset="100%" stopColor={strokeColor} stopOpacity="0.01" />
            </linearGradient>
          </defs>

          {/* Horizontal grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((frac, idx) => {
            const y = padY + frac * plotH;
            const labelVal = maxVal - frac * span;
            return (
              <g key={idx}>
                <line
                  x1={padX}
                  y1={y}
                  x2={width - padX}
                  y2={y}
                  stroke="#1e293b"
                  strokeDasharray="3 3"
                  strokeWidth="1"
                />
                <text
                  x={width - padX - 4}
                  y={y - 4}
                  textAnchor="end"
                  fill="#64748b"
                  fontSize="10"
                  fontFamily="monospace"
                >
                  {labelVal.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </text>
              </g>
            );
          })}

          {/* Optional SMA-20 Reference Line */}
          {sma20 && sma20 >= minVal && sma20 <= maxVal && (
            <g>
              <line
                x1={padX}
                y1={toY(sma20)}
                x2={width - padX}
                y2={toY(sma20)}
                stroke="#38bdf8"
                strokeDasharray="5 4"
                strokeWidth="1.2"
              />
              <text
                x={padX + 6}
                y={toY(sma20) - 5}
                fill="#38bdf8"
                fontSize="10"
                fontFamily="monospace"
              >
                SMA-20 ({sma20.toLocaleString()})
              </text>
            </g>
          )}

          {/* Area & Price Polyline */}
          <polygon points={areaStr} fill={`url(#${fillId})`} />
          <polyline
            fill="none"
            stroke={strokeColor}
            strokeWidth="2.2"
            points={pointsStr}
          />

          {/* Interactive hover columns */}
          {data.map((d, i) => {
            const cx = toX(i);
            const cy = toY(d.value);
            const colW = plotW / data.length;
            return (
              <g key={i}>
                <rect
                  x={cx - colW / 2}
                  y={padY}
                  width={colW}
                  height={plotH}
                  fill="transparent"
                  className="cursor-crosshair"
                  onMouseEnter={() => setHoverIdx(i)}
                />
                {hoverIdx === i && (
                  <>
                    <line
                      x1={cx}
                      y1={padY}
                      x2={cx}
                      y2={padY + plotH}
                      stroke="#94a3b8"
                      strokeDasharray="2 2"
                    />
                    <circle
                      cx={cx}
                      cy={cy}
                      r="4.5"
                      fill={strokeColor}
                      stroke="#0f172a"
                      strokeWidth="2"
                    />
                  </>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

/**
 * 2. Sovereign Yield Curve Chart (Nelson-Siegel Nominal Yield % vs Fisher Real Yield %)
 */
export function SovereignYieldCurveChart({
  fittedTenors,
  realYields,
  inflationBenchmark,
}: {
  fittedTenors: Record<string, number>;
  realYields: Record<string, number>;
  inflationBenchmark: number;
}) {
  const tenorsOrder = ["91D", "182D", "364D", "2Y", "3Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"];
  const points = tenorsOrder
    .filter((t) => fittedTenors[t] !== undefined)
    .map((t) => ({
      tenor: t,
      nominal: fittedTenors[t],
      real: realYields[t] ?? fittedTenors[t] - inflationBenchmark,
    }));

  if (points.length < 3) {
    return null;
  }

  const allVals = points.flatMap((p) => [p.nominal, p.real]);
  const minY = Math.min(...allVals, -15);
  const maxY = Math.max(...allVals, 25);
  const span = Math.max(1, maxY - minY);

  const width = 760;
  const height = 250;
  const padX = 28;
  const padY = 24;
  const plotW = width - padX * 2;
  const plotH = height - padY * 2;

  const toX = (i: number) => padX + (i / (points.length - 1)) * plotW;
  const toY = (v: number) => padY + plotH - ((v - minY) / span) * plotH;

  const nomLine = points.map((p, i) => `${toX(i).toFixed(1)},${toY(p.nominal).toFixed(1)}`).join(" ");
  const realLine = points.map((p, i) => `${toX(i).toFixed(1)},${toY(p.real).toFixed(1)}`).join(" ");
  const zeroY = toY(0);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between text-xs">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-amber-400 font-semibold">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-400 inline-block" />
            Nominal Sovereign Yield (% p.a.)
          </span>
          <span className="flex items-center gap-1.5 text-sky-400 font-semibold">
            <span className="h-2.5 w-2.5 rounded-full bg-sky-400 inline-block" />
            Fisher Real Yield vs {inflationBenchmark.toFixed(2)}% CPI
          </span>
        </div>
        <span className="font-mono text-slate-400">
          Nelson-Siegel Parametric Fit
        </span>
      </div>

      <div className="rounded-lg border border-slate-800/90 bg-slate-950/80 p-2">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
          {/* 0% Real Yield threshold line */}
          {zeroY >= padY && zeroY <= padY + plotH && (
            <line
              x1={padX}
              y1={zeroY}
              x2={width - padX}
              y2={zeroY}
              stroke="#475569"
              strokeDasharray="4 4"
              strokeWidth="1"
            />
          )}

          {/* Nominal and Real polylines */}
          <polyline fill="none" stroke="#fbbf24" strokeWidth="2.5" points={nomLine} />
          <polyline fill="none" stroke="#38bdf8" strokeWidth="2" strokeDasharray="5 3" points={realLine} />

          {/* Tenor nodes & labels */}
          {points.map((p, i) => {
            const cx = toX(i);
            const ny = toY(p.nominal);
            const ry = toY(p.real);
            return (
              <g key={p.tenor}>
                <circle cx={cx} cy={ny} r="4" fill="#fbbf24" />
                <text
                  x={cx}
                  y={ny - 8}
                  textAnchor="middle"
                  fill="#fde68a"
                  fontSize="9.5"
                  fontFamily="monospace"
                >
                  {p.nominal.toFixed(1)}%
                </text>

                <circle cx={cx} cy={ry} r="3.5" fill="#38bdf8" />
                <text
                  x={cx}
                  y={ry + 13}
                  textAnchor="middle"
                  fill="#7dd3fc"
                  fontSize="9"
                  fontFamily="monospace"
                >
                  {p.real.toFixed(1)}%
                </text>

                <text
                  x={cx}
                  y={height - 4}
                  textAnchor="middle"
                  fill="#94a3b8"
                  fontSize="10"
                  fontWeight="bold"
                  fontFamily="monospace"
                >
                  {p.tenor}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
