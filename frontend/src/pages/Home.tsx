import { Warning } from "@phosphor-icons/react";
import styled from "styled-components";

import {
  CashflowChart,
  CategoryDonut,
  ProjectionChart,
} from "../components/charts";
import { Card, Muted, PageTitle, Stack } from "../components/ui";
import { formatDate, formatMoney } from "../lib/format";
import {
  useBudget,
  useByCategory,
  useCashflow,
  useDashboardBalances,
  useOverview,
  useProjection,
  useTransactions,
} from "../lib/queries";
import type { TrafficLight } from "../lib/types";

const currentMonth = () => new Date().toISOString().slice(0, 7);

const LIGHT_TOKEN: Record<TrafficLight, "success" | "warning" | "danger"> = {
  green: "success",
  warning: "warning",
  danger: "danger",
};

const Hero = styled(Card)<{ $light: "success" | "warning" | "danger" }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  border-left: 4px solid ${({ theme, $light }) => theme.color[$light]};
`;

const HeroLabel = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

const HeroValue = styled.span<{ $light: "success" | "warning" | "danger" }>`
  font-size: ${({ theme }) => theme.fontSize.display};
  font-weight: ${({ theme }) => theme.fontWeight.bold};
  font-variant-numeric: tabular-nums;
  color: ${({ theme, $light }) => theme.color[$light]};
`;

const Progress = styled.div`
  height: 6px;
  border-radius: ${({ theme }) => theme.radius.pill};
  background: ${({ theme }) => theme.color.surfaceRaised};
  overflow: hidden;
  margin-top: ${({ theme }) => theme.space.sm};
`;

const ProgressFill = styled.div<{ $pct: number }>`
  height: 100%;
  width: ${({ $pct }) => Math.min(100, Math.max(0, $pct))}%;
  background: ${({ theme }) => theme.color.primary};
`;

const StatGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: ${({ theme }) => theme.space.lg};
`;

const Stat = styled(Card)`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
`;

const StatLabel = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

const StatValue = styled.span<{ $negative?: boolean }>`
  font-size: ${({ theme }) => theme.fontSize.xl};
  font-weight: ${({ theme }) => theme.fontWeight.semibold};
  font-variant-numeric: tabular-nums;
  color: ${({ theme, $negative }) =>
    $negative ? theme.color.danger : theme.color.text};
`;

const ChartGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: ${({ theme }) => theme.space.lg};
`;

const ChartCard = styled(Card)`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

const ChartTitle = styled.h2`
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
  font-weight: ${({ theme }) => theme.fontWeight.medium};
`;

const AlertRow = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => `${theme.space.sm} 0`};
  color: ${({ theme }) => theme.color.warning};
  font-size: ${({ theme }) => theme.fontSize.sm};

  & + & {
    border-top: 1px solid ${({ theme }) => theme.color.border};
  }
`;

const AccountGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: ${({ theme }) => theme.space.md};
`;

const AccountCard = styled(Card)`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
`;

const AccountBalances = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: ${({ theme }) => theme.space.md};
  font-variant-numeric: tabular-nums;
`;

export function Home() {
  const overview = useOverview();
  const balances = useDashboardBalances();
  const projection = useProjection();
  const byCategory = useByCategory();
  const cashflow = useCashflow(8);
  const review = useTransactions({ needs_review: true, page_size: 1 });
  const budget = useBudget(currentMonth());

  if (overview.isLoading) return <Muted>Loading dashboard…</Muted>;
  if (overview.isError || !overview.data)
    return <Muted>Could not load the dashboard.</Muted>;

  const o = overview.data;
  const light = LIGHT_TOKEN[o.traffic_light];
  const progressPct =
    (o.month_progress.elapsed_days / o.month_progress.total_days) * 100;

  const exceeded = (budget.data?.lines ?? []).filter(
    (l) =>
      l.category_id !== null &&
      Number.parseFloat(l.amount_usd) > 0 &&
      l.remaining_usd.startsWith("-"),
  );
  const unreviewedTotal = review.data?.total ?? 0;
  const hasAlerts = unreviewedTotal > 0 || exceeded.length > 0;

  return (
    <Stack $gap="xl">
      <PageTitle>Home</PageTitle>

      <Hero $light={light}>
        <HeroLabel>Safe to spend today</HeroLabel>
        <HeroValue $light={light}>
          {formatMoney(o.daily_allowance_usd, "USD")}
        </HeroValue>
        <Muted>
          {formatMoney(o.remaining_month_usd, "USD")} left this month ·{" "}
          {o.days_remaining_in_month} day
          {o.days_remaining_in_month === 1 ? "" : "s"} to go · projected month-end
          spend {formatMoney(o.projected_month_end_spend_usd, "USD")} vs ceiling{" "}
          {formatMoney(o.monthly_ceiling_usd, "USD")}
        </Muted>
        <Progress>
          <ProgressFill $pct={progressPct} />
        </Progress>
      </Hero>

      <StatGrid>
        <Stat>
          <StatLabel>Net worth (USD)</StatLabel>
          <StatValue $negative={o.net_worth_usd.startsWith("-")}>
            {formatMoney(o.net_worth_usd, "USD")}
          </StatValue>
          <Muted>
            available {formatMoney(o.available_usd, "USD")} after reserve &
            committed
          </Muted>
        </Stat>
        <Stat>
          <StatLabel>Monthly ceiling</StatLabel>
          <StatValue $negative={o.monthly_ceiling_usd.startsWith("-")}>
            {formatMoney(o.monthly_ceiling_usd, "USD")}
          </StatValue>
          <Muted>{o.months_remaining} months to {formatDate(o.academic_year_end)}</Muted>
        </Stat>
        <Stat>
          <StatLabel>Spent this month</StatLabel>
          <StatValue>{formatMoney(o.mtd_spend_usd, "USD")}</StatValue>
          <Muted>setup costs excluded from the pace</Muted>
        </Stat>
        <Stat>
          <StatLabel>Runway</StatLabel>
          <StatValue>
            {o.runway_days === null ? "—" : `${o.runway_days} days`}
          </StatValue>
          <Muted>at the current burn rate</Muted>
        </Stat>
      </StatGrid>

      <ChartGrid>
        <ChartCard>
          <ChartTitle>Projected balance to year end</ChartTitle>
          {projection.data && <ProjectionChart data={projection.data} />}
          {projection.data?.zero_crossing_date && (
            <Muted>
              Runs out around {formatDate(projection.data.zero_crossing_date)}.
            </Muted>
          )}
        </ChartCard>
        <ChartCard>
          <ChartTitle>This month by category</ChartTitle>
          {byCategory.data?.categories && (
            <CategoryDonut rows={byCategory.data.categories} />
          )}
        </ChartCard>
      </ChartGrid>

      <ChartCard>
        <ChartTitle>Spend by month</ChartTitle>
        {cashflow.data && <CashflowChart months={cashflow.data.months} />}
      </ChartCard>

      {hasAlerts && (
        <Card>
          <ChartTitle>Alerts</ChartTitle>
          {unreviewedTotal > 0 && (
            <AlertRow>
              <Warning size={16} weight="fill" />
              {unreviewedTotal} transaction{unreviewedTotal === 1 ? "" : "s"} need
              review
            </AlertRow>
          )}
          {exceeded.map((l) => (
            <AlertRow key={l.category_id}>
              <Warning size={16} weight="fill" />
              {l.name} is over budget by{" "}
              {formatMoney(l.remaining_usd.replace("-", ""), "USD")}
            </AlertRow>
          ))}
        </Card>
      )}

      <Stack $gap="md">
        <ChartTitle>Accounts</ChartTitle>
        <AccountGrid>
          {(balances.data?.accounts ?? []).map((a) => (
            <AccountCard key={a.id}>
              <strong>{a.name}</strong>
              <Muted as="span">
                {a.institution} · {a.kind.replace("_", " ")}
              </Muted>
              <AccountBalances>
                <span>{formatMoney(a.balance, a.currency)}</span>
                {a.currency !== "USD" && (
                  <Muted as="span">≈ {formatMoney(a.balance_usd, "USD")}</Muted>
                )}
              </AccountBalances>
            </AccountCard>
          ))}
        </AccountGrid>
      </Stack>
    </Stack>
  );
}
