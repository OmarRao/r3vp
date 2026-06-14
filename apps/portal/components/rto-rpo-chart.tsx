"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface TrendPoint {
  date: string;
  avg_rto_mins: number;
  avg_rpo_mins: number;
}

interface RtoRpoChartProps {
  data: TrendPoint[];
}

export function RtoRpoChart({ data }: RtoRpoChartProps) {
  if (!data.length) {
    return (
      <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
        No test data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis unit=" min" tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v: number) => `${v} min`} />
        <Legend />
        <Line
          type="monotone"
          dataKey="avg_rto_mins"
          name="Avg RTO"
          stroke="#00B336"
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="avg_rpo_mins"
          name="Avg RPO"
          stroke="#3B82F6"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
