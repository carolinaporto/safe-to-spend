import { CaretLeft, CaretRight, Warning } from "@phosphor-icons/react";
import { useState } from "react";
import styled from "styled-components";

import { AddTransactionForm } from "../components/AddTransactionForm";
import {
  CashflowChart,
  CategoryDonut,
  ProjectionChart,
} from "../components/charts";
import {
  Card,
  GhostButton,
  Muted,
  PageTitle,
  Row,
  Stack,
} from "../components/ui";
import { formatDate, formatMoney } from "../lib/format";
import {
  useBudget,
  useCards,
  useCashflow,
  useDashboardBalances,
  useMonthSummary,
  useOverview,
  useProjection,
  useTransactions,
} from "../lib/queries";
import type { TrafficLight } from "../lib/types";

const currentMonth = () => new Date().toISOString().slice(0, 7);

function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });
}

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
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
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
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
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

const Spread = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.md};
`;

const Stepper = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
`;

const StepBtn = styled(GhostButton)`
  padding: ${({ theme }) => `${theme.space.xxs} ${theme.space.sm}`};
`;

const MonthTotals = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.lg};
  align-items: baseline;
  font-variant-numeric: tabular-nums;
`;

const BigNum = styled.span`
  font-size: ${({ theme }) => theme.fontSize.xl};
  font-weight: ${({ theme }) => theme.fontWeight.semibold};
`;

// One tight row per account instead of a grid of big cards.
const AcctList = styled.div`
  display: flex;
  flex-direction: column;
`;

const AcctRow = styled.div<{ $alert?: boolean }>`
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.sm} 0`};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-variant-numeric: tabular-nums;
  color: ${({ theme, $alert }) =>
    $alert ? theme.color.warning : theme.color.text};

  & + & {
    border-top: 1px solid ${({ theme }) => theme.color.border};
  }
`;

const AcctRight = styled.div`
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: ${({ theme }) => theme.space.xxs};
  text-align: right;
`;

// Dashboard on the left, a persistent add form on the right. On narrow
// screens it collapses to one column with the form right under the hero.
const Split = styled.div`
  display: grid;
  grid-template-columns: minmax(0, 1fr) 20rem;
  gap: ${({ theme }) => theme.space.xl};
  align-items: start;

  @media (max-width: ${({ theme }) => theme.bp.lg}) {
    grid-template-columns: 1fr;
  }
`;

const Aside = styled.div`
  position: sticky;
  top: ${({ theme }) => theme.space.xl};

  @media (max-width: ${({ theme }) => theme.bp.lg}) {
    position: static;
    order: -1;
  }
`;

export function Home() {
  const [month, setMonth] = useState(currentMonth());
  const overview = useOverview();
  const balances = useDashboardBalances();
  const projection = useProjection();
  const monthView = useMonthSummary(month);
  const cashflow = useCashflow(6);
  const review = useTransactions({ needs_review: true, page_size: 1 });
  const budget = useBudget(currentMonth());
  const cards = useCards();

  if (overview.isLoading) return <Muted>Loading dashboard…</Muted>;
  if (overview.isError || !overview.data)
    return <Muted>Could not load the dashboard.</Muted>;

  const o = overview.data;
  const overPace = o.daily_allowance_usd.startsWith("-");
  const light = overPace ? "danger" : LIGHT_TOKEN[o.traffic_light];
  const progressPct =
    (o.month_progress.elapsed_days / o.month_progress.total_days) * 100;

  const exceeded = (budget.data?.lines ?? []).filter(
    (l) =>
      l.category_id !== null &&
      Number.parseFloat(l.amount_usd) > 0 &&
      l.remaining_usd.startsWith("-"),
  );
  const unreviewedTotal = review.data?.total ?? 0;
  const cardPanels = cards.data ?? [];
  const dueCards = cardPanels.filter((c) => c.alert);
  const cardByAccount = new Map(cardPanels.map((c) => [c.account_id, c]));
  const hasReceivables =
    o.receivables_usd !== "0.00" && !o.receivables_usd.startsWith("-");
  const hasAlerts =
    unreviewedTotal > 0 ||
    exceeded.length > 0 ||
    dueCards.length > 0 ||
    hasReceivables;

  return (
    <Stack $gap="xl">
      <PageTitle>Home</PageTitle>

      <Hero $light={light}>
        <HeroLabel>
          {overPace ? "Over pace — ease off" : "Safe to spend today"}
        </HeroLabel>
        <HeroValue $light={light}>
          {formatMoney(o.daily_allowance_usd, "USD")}
        </HeroValue>
        <Muted>
          Pace {formatMoney(o.daily_rate_usd, "USD")}/day ·{" "}
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

      <Split>
        <Stack $gap="xl">
      <StatGrid>
        <Stat>
          <StatLabel>Net worth (USD)</StatLabel>
          <StatValue $negative={o.net_worth_usd.startsWith("-")}>
            {formatMoney(o.net_worth_usd, "USD")}
          </StatValue>
          <Muted>
            {formatMoney(o.available_usd, "USD")} free to spend, after{" "}
            {formatMoney(o.emergency_reserve_usd, "USD")} reserve,{" "}
            {formatMoney(o.future_committed_costs_usd, "USD")} committed &{" "}
            {formatMoney(o.future_recurring_costs_usd, "USD")} in recurring bills
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
          <Muted>setup & recurring bills excluded from the pace</Muted>
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
          <Spread>
            <ChartTitle>{monthLabel(month)}</ChartTitle>
            <Stepper>
              <StepBtn
                type="button"
                aria-label="Previous month"
                onClick={() => setMonth((m) => shiftMonth(m, -1))}
              >
                <CaretLeft size={14} />
              </StepBtn>
              {month !== currentMonth() && (
                <StepBtn
                  type="button"
                  onClick={() => setMonth(currentMonth())}
                >
                  Today
                </StepBtn>
              )}
              <StepBtn
                type="button"
                aria-label="Next month"
                onClick={() => setMonth((m) => shiftMonth(m, 1))}
              >
                <CaretRight size={14} />
              </StepBtn>
            </Stepper>
          </Spread>
          <MonthTotals>
            <div>
              <BigNum>
                {formatMoney(monthView.data?.spent_usd ?? "0", "USD")}
              </BigNum>{" "}
              <Muted as="span">spent</Muted>
            </div>
            {monthView.data &&
              monthView.data.scheduled_usd !== "0.00" && (
                <div>
                  <Muted as="span">
                    + {formatMoney(monthView.data.scheduled_usd, "USD")}{" "}
                    scheduled
                  </Muted>
                </div>
              )}
          </MonthTotals>
          {monthView.data && monthView.data.categories.length > 0 ? (
            <CategoryDonut rows={monthView.data.categories} />
          ) : (
            <Muted>Nothing logged for {monthLabel(month)} yet.</Muted>
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
          {dueCards.map((c) => (
            <AlertRow key={c.account_id}>
              <Warning size={16} weight="fill" />
              {c.name} statement of{" "}
              {formatMoney(c.statement_balance_usd, "USD")} is due
              {c.due_date ? ` ${formatDate(c.due_date)}` : ""} (
              {c.days_until_due} day{c.days_until_due === 1 ? "" : "s"})
            </AlertRow>
          ))}
          {hasReceivables && (
            <AlertRow>
              <Warning size={16} weight="fill" />
              {formatMoney(o.receivables_usd, "USD")} owed to you is still
              unsettled — see People
            </AlertRow>
          )}
        </Card>
      )}

      <Card>
        <ChartTitle>Accounts</ChartTitle>
        <AcctList>
          {(balances.data?.accounts ?? [])
            .filter((a) => a.is_active)
            .map((a) => {
            const cardInfo = cardByAccount.get(a.id);
            return (
              <AcctRow key={a.id} $alert={cardInfo?.alert}>
                <Row $gap="sm">
                  <span>{a.name}</span>
                  <Muted as="span">
                    {a.institution || a.kind.replace("_", " ")}
                  </Muted>
                </Row>
                <AcctRight>
                  <span>{formatMoney(a.balance, a.currency)}</span>
                  {a.currency !== "USD" && (
                    <Muted as="span">
                      ≈ {formatMoney(a.balance_usd, "USD")}
                    </Muted>
                  )}
                  {cardInfo?.due_date && (
                    <Muted as="span">
                      statement{" "}
                      {formatMoney(cardInfo.statement_balance_usd, "USD")} ·
                      due {formatDate(cardInfo.due_date)}
                    </Muted>
                  )}
                </AcctRight>
              </AcctRow>
            );
          })}
        </AcctList>
      </Card>
        </Stack>

        <Aside>
          <AddTransactionForm />
        </Aside>
      </Split>
    </Stack>
  );
}
