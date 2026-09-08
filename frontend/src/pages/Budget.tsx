import { CaretLeft, CaretRight, Copy } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
import styled from "styled-components";

import { DecimalInput } from "../components/DecimalInput";
import {
  Button,
  Card,
  ErrorText,
  GhostButton,
  Muted,
  PageTitle,
  Row,
  Stack,
} from "../components/ui";
import { ApiError } from "../lib/api";
import { formatMoney, shortMonth, toPlotNumber } from "../lib/format";
import { useMeta } from "../lib/meta";
import { useBudget, useCopyBudget, useSaveBudget } from "../lib/queries";
import type { BudgetLine } from "../lib/types";

function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  const idx = y * 12 + (m - 1) + delta;
  return `${Math.floor(idx / 12)}-${String((idx % 12) + 1).padStart(2, "0")}`;
}

const Line = styled.div`
  display: grid;
  grid-template-columns: 1.4fr 7rem 5.5rem 1fr 7rem;
  gap: ${({ theme }) => theme.space.md};
  align-items: center;
  padding: ${({ theme }) => `${theme.space.sm} 0`};

  & + & {
    border-top: 1px solid ${({ theme }) => theme.color.border};
  }

  @media (max-width: ${({ theme }) => theme.bp.sm}) {
    grid-template-columns: 1fr auto auto;
    grid-template-areas:
      "name name name"
      "bar bar bar"
      "amount roll remaining";
    gap: ${({ theme }) => theme.space.sm};
    column-gap: ${({ theme }) => theme.space.md};

    & > *:nth-child(1) {
      grid-area: name;
    }
    & > *:nth-child(2) {
      grid-area: amount;
    }
    & > *:nth-child(3) {
      grid-area: roll;
    }
    & > *:nth-child(4) {
      grid-area: bar;
    }
    & > *:nth-child(5) {
      grid-area: remaining;
      text-align: right;
    }
  }
`;

const Name = styled.span<{ $strong?: boolean }>`
  font-weight: ${({ theme, $strong }) =>
    $strong ? theme.fontWeight.semibold : theme.fontWeight.regular};
`;

const Bar = styled.div`
  height: 8px;
  border-radius: ${({ theme }) => theme.radius.pill};
  background: ${({ theme }) => theme.color.surfaceRaised};
  overflow: hidden;
`;

const BarFill = styled.div<{ $pct: number; $over: boolean }>`
  height: 100%;
  width: ${({ $pct }) => Math.min(100, Math.max(0, $pct))}%;
  background: ${({ theme, $over }) =>
    $over ? theme.color.danger : theme.color.success};
`;

const Remaining = styled.span<{ $negative: boolean }>`
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: ${({ theme, $negative }) =>
    $negative ? theme.color.danger : theme.color.textMuted};
`;

const SmallInput = styled(DecimalInput)`
  padding: ${({ theme }) => `${theme.space.xs} ${theme.space.sm}`};
`;

interface Draft {
  amount: string;
  rollover: boolean;
}

export function Budget() {
  const [month, setMonth] = useState(() =>
    new Date().toISOString().slice(0, 7),
  );
  const { data, isLoading } = useBudget(month);
  const save = useSaveBudget(month);
  const copy = useCopyBudget(month);
  const meta = useMeta();
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!data) return;
    const next: Record<string, Draft> = {};
    for (const line of data.lines) {
      next[String(line.category_id)] = {
        amount: line.amount_usd,
        rollover: line.rollover,
      };
    }
    setDrafts(next);
  }, [data]);

  const dirty = useMemo(() => {
    if (!data) return false;
    return data.lines.some((l) => {
      const d = drafts[String(l.category_id)];
      return d && (d.amount !== l.amount_usd || d.rollover !== l.rollover);
    });
  }, [data, drafts]);

  if (isLoading || !data) return <Muted>Loading budget…</Muted>;

  const key = (l: BudgetLine) => String(l.category_id);
  const rank = (l: BudgetLine) => {
    if (l.category_id === null) return 0;
    const d = drafts[key(l)];
    const budgeted = Number.parseFloat(d?.amount ?? l.amount_usd);
    const spent = Number.parseFloat(l.spent_usd);
    return budgeted > 0 ? 1 : spent > 0 ? 2 : 3;
  };
  const rows = [...data.lines].sort(
    (a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name),
  );

  async function persist() {
    setError(null);
    try {
      await save.mutateAsync(
        rows.map((l) => ({
          category_id: l.category_id,
          amount_usd: drafts[key(l)]?.amount ?? "0",
          rollover: drafts[key(l)]?.rollover ?? false,
        })),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save");
    }
  }

  async function copyPrevious() {
    setError(null);
    try {
      await copy.mutateAsync();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Nothing to copy",
      );
    }
  }


  return (
    <Stack $gap="lg">
      <PageTitle>Budget</PageTitle>

      <Row $gap="md">
        <GhostButton
          type="button"
          onClick={() => setMonth(shiftMonth(month, -1))}
          aria-label="Previous month"
        >
          <CaretLeft size={16} />
        </GhostButton>
        <strong>{shortMonth(`${month}-01`)}</strong>
        <GhostButton
          type="button"
          onClick={() => setMonth(shiftMonth(month, 1))}
          aria-label="Next month"
        >
          <CaretRight size={16} />
        </GhostButton>
        {!meta.demo_mode && (
          <GhostButton type="button" onClick={copyPrevious}>
            <Copy size={16} /> Copy last month
          </GhostButton>
        )}
      </Row>

      <Card>
        {rows.map((line) => {
          const d = drafts[key(line)] ?? {
            amount: line.amount_usd,
            rollover: line.rollover,
          };
          const budgeted =
            toPlotNumber(d.amount) + toPlotNumber(line.rollover_in_usd);
          const spent = toPlotNumber(line.spent_usd);
          const hasBudget = budgeted > 0;
          const over = spent > budgeted;
          const pct = hasBudget ? (spent / budgeted) * 100 : spent > 0 ? 100 : 0;
          return (
            <Line key={key(line)}>
              <Name $strong={line.category_id === null}>
                {line.name}
                {toPlotNumber(line.rollover_in_usd) > 0 && (
                  <Muted as="span">
                    {" "}
                    +{formatMoney(line.rollover_in_usd, "USD")} rolled over
                  </Muted>
                )}
              </Name>
              <SmallInput
                aria-label={`${line.name} budget`}
                disabled={meta.demo_mode}
                value={d.amount}
                onChange={(e) =>
                  setDrafts((s) => ({
                    ...s,
                    [key(line)]: { ...d, amount: e.target.value },
                  }))
                }
              />
              <label>
                <input
                  type="checkbox"
                  aria-label={`${line.name} rollover`}
                  disabled={meta.demo_mode}
                  checked={d.rollover}
                  onChange={(e) =>
                    setDrafts((s) => ({
                      ...s,
                      [key(line)]: { ...d, rollover: e.target.checked },
                    }))
                  }
                />{" "}
                <Muted as="span">roll</Muted>
              </label>
              <Bar>
                <BarFill $pct={pct} $over={over && (hasBudget || spent > 0)} />
              </Bar>
              <Remaining $negative={over && spent > 0}>
                {formatMoney(line.spent_usd, "USD")}
                {hasBudget && ` / ${formatMoney(d.amount, "USD")}`}
              </Remaining>
            </Line>
          );
        })}
      </Card>

      {error && <ErrorText>{error}</ErrorText>}

      {!meta.demo_mode && (
        <Row>
          <Button type="button" disabled={!dirty || save.isPending} onClick={persist}>
            {save.isPending ? "Saving…" : "Save budget"}
          </Button>
        </Row>
      )}
    </Stack>
  );
}
