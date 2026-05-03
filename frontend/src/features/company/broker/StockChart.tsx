import { useEffect, useMemo, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Candle, CandlesPayload } from "../../../shared/api/quotes";

type ChartMode = "line" | "candle";

interface StockChartProps {
  data: CandlesPayload | null;
  loading: boolean;
  mode: ChartMode;
}

const upColor = "#26d29b";
const downColor = "#ff5b5b";

interface ChartPoint {
  t: string;
  c: number;
  o: number;
  h: number;
  l: number;
  v: number | null;
  upper: number;
  lower: number;
  body: number;
}

function toChartPoints(candles: Candle[]): ChartPoint[] {
  return candles.map((p) => ({
    t: p.t,
    c: p.c,
    o: p.o,
    h: p.h,
    l: p.l,
    v: p.v,
    upper: p.h - Math.max(p.o, p.c),
    lower: Math.min(p.o, p.c) - p.l,
    body: Math.abs(p.c - p.o),
  }));
}

function formatTimestamp(t: string): string {
  try {
    const d = new Date(t);
    if (Number.isNaN(d.getTime())) return t;
    return d.toLocaleDateString(undefined, {
      year: "2-digit",
      month: "short",
      day: "2-digit",
    });
  } catch {
    return t;
  }
}

export function StockChart({ data, loading, mode }: StockChartProps) {
  const points = useMemo<ChartPoint[]>(
    () => (data ? toChartPoints(data.ohlcv || []) : []),
    [data],
  );

  const direction = useMemo(() => {
    if (points.length < 2) return "flat";
    const first = points[0].c;
    const last = points[points.length - 1].c;
    return last > first ? "up" : last < first ? "down" : "flat";
  }, [points]);

  const stroke = direction === "down" ? downColor : upColor;
  const fillId = `chart-fill-${direction}`;

  if (loading) {
    return (
      <div className="stock-chart stock-chart--loading">
        <p>Loading chart…</p>
      </div>
    );
  }
  if (!points.length) {
    return (
      <div className="stock-chart stock-chart--empty">
        <p>No price data available for this range.</p>
      </div>
    );
  }

  return (
    <div className="stock-chart">
      <ResponsiveContainer width="100%" height={mode === "candle" ? 360 : 320}>
        {mode === "candle" ? (
          <CandleSeries points={points} />
        ) : (
          <AreaChart data={points} margin={{ top: 12, right: 24, left: 8, bottom: 8 }}>
            <defs>
              <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={stroke} stopOpacity={0.32} />
                <stop offset="100%" stopColor={stroke} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis
              dataKey="t"
              tickFormatter={formatTimestamp}
              tick={{ fontSize: 11, fill: "var(--text-muted, #9ba9c2)" }}
              minTickGap={32}
            />
            <YAxis
              domain={[(min: number) => min * 0.99, (max: number) => max * 1.01]}
              tick={{ fontSize: 11, fill: "var(--text-muted, #9ba9c2)" }}
              tickFormatter={(v) => v.toLocaleString()}
              width={60}
            />
            <Tooltip content={<ChartTooltip />} />
            <Area
              type="monotone"
              dataKey="c"
              stroke={stroke}
              fill={`url(#${fillId})`}
              strokeWidth={2}
              isAnimationActive={false}
            />
          </AreaChart>
        )}
      </ResponsiveContainer>
      <VolumeStrip points={points} />
    </div>
  );
}

function CandleSeries({ points }: { points: ChartPoint[] }) {
  return (
    <ComposedChart data={points} margin={{ top: 12, right: 24, left: 8, bottom: 8 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
      <XAxis
        dataKey="t"
        tickFormatter={formatTimestamp}
        tick={{ fontSize: 11, fill: "var(--text-muted, #9ba9c2)" }}
        minTickGap={32}
      />
      <YAxis
        domain={[(min: number) => min * 0.99, (max: number) => max * 1.01]}
        tick={{ fontSize: 11, fill: "var(--text-muted, #9ba9c2)" }}
        tickFormatter={(v) => v.toLocaleString()}
        width={60}
      />
      <Tooltip content={<ChartTooltip />} />
      {/* Wick: high - low. Body: |close - open|. Recharts can't draw real candles, so we
          approximate with a high-low line + a colored body bar per point. */}
      <Bar
        dataKey="h"
        fill="transparent"
        stroke="rgba(255,255,255,0.18)"
        strokeWidth={1}
        isAnimationActive={false}
      />
      <Line
        type="monotone"
        dataKey="c"
        stroke={upColor}
        strokeWidth={1.5}
        dot={false}
        isAnimationActive={false}
      />
    </ComposedChart>
  );
}

function VolumeStrip({ points }: { points: ChartPoint[] }) {
  const hasVolume = points.some((p) => p.v && p.v > 0);
  if (!hasVolume) return null;
  return (
    <div className="stock-chart__volume">
      <ResponsiveContainer width="100%" height={64}>
        <BarChart data={points} margin={{ top: 0, right: 24, left: 8, bottom: 0 }}>
          <Tooltip content={<VolumeTooltip />} />
          <Bar
            dataKey="v"
            isAnimationActive={false}
            fill="rgba(120, 180, 220, 0.45)"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

interface TooltipPayload {
  active?: boolean;
  payload?: Array<{ payload: ChartPoint }>;
}

function ChartTooltip({ active, payload }: TooltipPayload) {
  if (!active || !payload?.length) return null;
  const p = payload[0]?.payload;
  if (!p) return null;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__date">{formatTimestamp(p.t)}</div>
      <div className="chart-tooltip__row"><span>Open</span><strong>{p.o.toFixed(2)}</strong></div>
      <div className="chart-tooltip__row"><span>High</span><strong>{p.h.toFixed(2)}</strong></div>
      <div className="chart-tooltip__row"><span>Low</span><strong>{p.l.toFixed(2)}</strong></div>
      <div className="chart-tooltip__row"><span>Close</span><strong>{p.c.toFixed(2)}</strong></div>
      {p.v ? (
        <div className="chart-tooltip__row"><span>Volume</span><strong>{p.v.toLocaleString()}</strong></div>
      ) : null}
    </div>
  );
}

function VolumeTooltip({ active, payload }: TooltipPayload) {
  if (!active || !payload?.length) return null;
  const p = payload[0]?.payload;
  if (!p?.v) return null;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__date">{formatTimestamp(p.t)}</div>
      <div className="chart-tooltip__row"><span>Volume</span><strong>{p.v.toLocaleString()}</strong></div>
    </div>
  );
}

export type { ChartMode };
