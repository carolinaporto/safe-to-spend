import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useTheme } from "styled-components";

import { formatMoney, shortMonth, toPlotNumber } from "../lib/format";
import type { Theme } from "../theme";
import type {
  CashflowMonth,
  CategorySpend,
  Projection,
  ProviderSummary,
  Transfer,
} from "../lib/types";

const NATURE_ORDER = ["essential", "discretionary", "setup", "fee"] as const;

// Recharts is styled through props, not CSS — these read from the theme.
const tooltipStyle = (theme: Theme) => ({
  background: theme.color.surfaceRaised,
  border: `1px solid ${theme.color.border}`,
  borderRadius: 8,
  color: theme.color.text,
});

const usd = (v: number | string) => formatMoney(String(v), "USD");

const legendLabel = (theme: Theme) => (value: string) => (
  <span style={{ color: theme.color.textMuted }}>{value}</span>
);

// Deterministic colour for a category donut slice: category colour if set,
// else a shade derived from its nature.
function sliceColor(row: CategorySpend, natureColors: Record<string, string>) {
  if (row.color) return row.color;
  return natureColors[row.nature ?? "essential"] ?? natureColors.essential;
}

export function ProjectionChart({ data }: { data: Projection }) {
  const theme = useTheme();
  const points = data.points.map((p) => ({
    date: p.date,
    balance: toPlotNumber(p.balance_usd),
  }));
  const zero = data.zero_crossing_date;
  const zeroPoint = zero
    ? points.find((p) => p.date >= zero) ?? points[points.length - 1]
    : null;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <defs>
          <linearGradient id="proj" x1="0" y1="0" x2="0" y2="1">
            <stop
              offset="0%"
              stopColor={theme.color.primary}
              stopOpacity={0.35}
            />
            <stop
              offset="100%"
              stopColor={theme.color.primary}
              stopOpacity={0}
            />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tickFormatter={shortMonth}
          stroke={theme.color.textFaint}
          fontSize={12}
          minTickGap={40}
        />
        <YAxis
          stroke={theme.color.textFaint}
          fontSize={12}
          width={64}
          tickFormatter={(v) => formatMoney(String(v), "USD")}
        />
        <Tooltip
          contentStyle={tooltipStyle(theme)}
          formatter={usd}
          labelFormatter={(l) => shortMonth(String(l))}
        />
        <ReferenceLine y={0} stroke={theme.color.border} />
        {data.committed_costs.map((c) => (
          <ReferenceLine
            key={`${c.due_date}-${c.label}`}
            x={c.due_date}
            stroke={theme.color.warning}
            strokeDasharray="3 3"
            label={{
              value: c.label,
              position: "insideTopRight",
              fill: theme.color.textMuted,
              fontSize: 10,
            }}
          />
        ))}
        <Area
          type="monotone"
          dataKey="balance"
          stroke={theme.color.primary}
          strokeWidth={2}
          fill="url(#proj)"
        />
        {zeroPoint && (
          <ReferenceDot
            x={zeroPoint.date}
            y={0}
            r={5}
            fill={theme.color.danger}
            stroke="none"
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function CategoryDonut({ rows }: { rows: CategorySpend[] }) {
  const theme = useTheme();
  const data = rows
    .filter((r) => toPlotNumber(r.amount_usd) > 0)
    .map((r) => ({
      name: r.name,
      value: toPlotNumber(r.amount_usd),
      fill: sliceColor(r, theme.nature),
    }));

  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius={62}
          outerRadius={96}
          paddingAngle={1}
          stroke={theme.color.surface}
        >
          {data.map((d) => (
            <Cell key={d.name} fill={d.fill} />
          ))}
        </Pie>
        <Tooltip contentStyle={tooltipStyle(theme)} formatter={usd} />
        <Legend formatter={legendLabel(theme)} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function TransferCostChart({ transfers }: { transfers: Transfer[] }) {
  const theme = useTheme();
  const ordered = [...transfers].sort((a, b) => a.date.localeCompare(b.date));
  let running = 0;
  const data = ordered.map((t) => {
    running += toPlotNumber(t.fx_cost_usd);
    return { date: t.date, cumulative: Number(running.toFixed(2)) };
  });

  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <defs>
          <linearGradient id="fxcost" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={theme.color.warning} stopOpacity={0.35} />
            <stop offset="100%" stopColor={theme.color.warning} stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tickFormatter={shortMonth}
          stroke={theme.color.textFaint}
          fontSize={12}
          minTickGap={40}
        />
        <YAxis
          stroke={theme.color.textFaint}
          fontSize={12}
          width={64}
          tickFormatter={(v) => formatMoney(String(v), "USD")}
        />
        <Tooltip contentStyle={tooltipStyle(theme)} formatter={usd} />
        <Area
          type="monotone"
          dataKey="cumulative"
          name="Cumulative FX cost"
          stroke={theme.color.warning}
          strokeWidth={2}
          fill="url(#fxcost)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function ProviderRateChart({
  providers,
}: {
  providers: ProviderSummary[];
}) {
  const theme = useTheme();
  const data = providers.map((p) => ({
    provider: p.provider,
    rate: toPlotNumber(p.avg_effective_rate),
  }));

  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <XAxis
          dataKey="provider"
          stroke={theme.color.textFaint}
          fontSize={12}
        />
        <YAxis
          stroke={theme.color.textFaint}
          fontSize={12}
          width={64}
          domain={["auto", "auto"]}
        />
        <Tooltip
          cursor={{ fill: theme.color.surfaceRaised }}
          contentStyle={tooltipStyle(theme)}
        />
        <Bar dataKey="rate" name="Avg effective rate" fill={theme.color.primary} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function CashflowChart({ months }: { months: CashflowMonth[] }) {
  const theme = useTheme();
  const data = months.map((m) => ({
    month: m.month,
    essential: toPlotNumber(m.essential),
    discretionary: toPlotNumber(m.discretionary),
    setup: toPlotNumber(m.setup),
    fee: toPlotNumber(m.fee),
    income: toPlotNumber(m.income),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <XAxis
          dataKey="month"
          tickFormatter={shortMonth}
          stroke={theme.color.textFaint}
          fontSize={12}
        />
        <YAxis
          stroke={theme.color.textFaint}
          fontSize={12}
          width={64}
          tickFormatter={(v) => formatMoney(String(v), "USD")}
        />
        <Tooltip
          cursor={{ fill: theme.color.surfaceRaised }}
          contentStyle={tooltipStyle(theme)}
          formatter={usd}
          labelFormatter={(l) => shortMonth(String(l))}
        />
        <Legend formatter={legendLabel(theme)} />
        {NATURE_ORDER.map((nature) => (
          <Bar
            key={nature}
            dataKey={nature}
            stackId="spend"
            fill={theme.nature[nature]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
