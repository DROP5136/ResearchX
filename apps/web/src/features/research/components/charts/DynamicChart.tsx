import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartSpec } from "@/types/api";

const COLORS = ["#0d9488", "#537280", "#0f766e", "#9db3bd", "#14b8a6", "#3b4e59"];

export function DynamicChart({ chart }: { chart: ChartSpec }) {
  const type = (chart.chart_type || chart.type || "line").toLowerCase();
  const data = Array.isArray(chart.data) ? chart.data : [];
  const title = chart.title || "Chart";
  const xKey = chart.x_axis || chart.x || (data[0] ? Object.keys(data[0])[0] : "x");
  const seriesNames = (chart.series || [])
    .map((s) => (typeof s === "string" ? s : s.name))
    .filter(Boolean);

  const numericKeys =
    seriesNames.length > 0
      ? seriesNames
      : data[0]
        ? Object.keys(data[0]).filter((k) => k !== xKey && typeof data[0][k] === "number")
        : [];

  if (!data.length) {
    return (
      <div className="rounded-xl border border-dashed border-ink-200 p-6 text-sm text-ink-500 dark:border-ink-700">
        No chart data for “{title}”.
      </div>
    );
  }

  return (
    <div className="rx-panel p-4">
      <h3 className="mb-4 font-display text-lg">{title}</h3>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {type.includes("pie") || type.includes("donut") ? (
            <PieChart>
              <Pie data={data} dataKey={numericKeys[0] || "value"} nameKey={xKey} innerRadius={type.includes("donut") ? 50 : 0} outerRadius={90}>
                {data.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          ) : type.includes("area") ? (
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.3} />
              <XAxis dataKey={xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {numericKeys.map((k, i) => (
                <Area key={k} type="monotone" dataKey={k} stroke={COLORS[i % COLORS.length]} fill={COLORS[i % COLORS.length]} fillOpacity={0.2} />
              ))}
            </AreaChart>
          ) : type.includes("bar") ? (
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.3} />
              <XAxis dataKey={xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {numericKeys.map((k, i) => (
                <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} />
              ))}
            </BarChart>
          ) : (
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.3} />
              <XAxis dataKey={xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {numericKeys.map((k, i) => (
                <Line key={k} type="monotone" dataKey={k} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={false} />
              ))}
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
