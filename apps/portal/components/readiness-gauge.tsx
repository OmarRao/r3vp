"use client";

import { RadialBarChart, RadialBar, PolarAngleAxis } from "recharts";

interface ReadinessGaugeProps {
  score: number; // 0–100
}

function scoreColor(score: number): string {
  if (score >= 80) return "#00B336";
  if (score >= 50) return "#F59E0B";
  return "#EF4444";
}

export function ReadinessGauge({ score }: ReadinessGaugeProps) {
  const data = [{ value: score, fill: scoreColor(score) }];

  return (
    <div className="relative flex items-center justify-center">
      <RadialBarChart
        width={160}
        height={160}
        cx={80}
        cy={80}
        innerRadius={55}
        outerRadius={75}
        barSize={14}
        data={data}
        startAngle={180}
        endAngle={0}
      >
        <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
        <RadialBar background dataKey="value" cornerRadius={7} angleAxisId={0} />
      </RadialBarChart>
      <span className="absolute text-3xl font-bold text-gray-800">{score}</span>
    </div>
  );
}
