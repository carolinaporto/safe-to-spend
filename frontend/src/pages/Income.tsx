import styled from "styled-components";

import {
  Card,
  Muted,
  PageTitle,
  Stack,
  Table,
  TableScroll,
  Td,
  Th,
} from "../components/ui";
import { formatDate, formatMoney } from "../lib/format";
import { useAccounts, useIncomeSummary } from "../lib/queries";

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

const StatValue = styled.span<{ $tone?: "warning" }>`
  font-size: ${({ theme }) => theme.fontSize.xl};
  font-weight: ${({ theme }) => theme.fontWeight.semibold};
  font-variant-numeric: tabular-nums;
  color: ${({ theme, $tone }) =>
    $tone === "warning" ? theme.color.warning : theme.color.text};
`;

const SectionTitle = styled.h2`
  font-size: ${({ theme }) => theme.fontSize.lg};
  margin-bottom: ${({ theme }) => theme.space.md};
`;

export function Income() {
  const summary = useIncomeSummary();
  const accounts = useAccounts();

  if (summary.isLoading) return <Muted>Loading…</Muted>;
  if (summary.isError || !summary.data)
    return <Muted>Could not load the income summary.</Muted>;

  const s = summary.data;
  const accountName = new Map(
    (accounts.data ?? []).map((a) => [a.id, a.name] as const),
  );

  return (
    <Stack $gap="xl">
      <PageTitle>Income</PageTitle>

      <StatGrid>
        <Stat>
          <StatLabel>Funding received</StatLabel>
          <StatValue>{formatMoney(s.total_funding_usd, "USD")}</StatValue>
          <Muted>{formatMoney(s.total_funding_brl, "BRL")} in BRL terms</Muted>
        </Stat>
        <Stat>
          <StatLabel>Converted to USD</StatLabel>
          <StatValue>{formatMoney(s.converted_usd, "USD")}</StatValue>
          <Muted>from {formatMoney(s.converted_brl, "BRL")}</Muted>
        </Stat>
        <Stat>
          <StatLabel>Still in BRL</StatLabel>
          <StatValue>{formatMoney(s.still_in_brl, "BRL")}</StatValue>
          <Muted>≈ {formatMoney(s.still_in_brl_usd, "USD")}</Muted>
        </Stat>
        <Stat>
          <StatLabel>Cumulative FX cost</StatLabel>
          <StatValue $tone="warning">
            {formatMoney(s.cumulative_fx_cost_usd, "USD")}
          </StatValue>
          <Muted>lost to spread &amp; fees converting BRL → USD</Muted>
        </Stat>
      </StatGrid>

      <Card>
        <SectionTitle>Funding entries</SectionTitle>
        {s.entries.length === 0 ? (
          <Muted>
            No funding transactions yet. Tag income in the “Funding” category to
            see it here.
          </Muted>
        ) : (
          <TableScroll>
            <Table>
              <thead>
                <tr>
                  <Th>Date</Th>
                  <Th>Account</Th>
                  <Th $align="right">Amount</Th>
                  <Th $align="right">USD</Th>
                </tr>
              </thead>
              <tbody>
                {s.entries.map((e) => (
                  <tr key={e.id}>
                    <Td>{formatDate(e.date)}</Td>
                    <Td>{accountName.get(e.account_id) ?? "—"}</Td>
                    <Td $align="right">
                      {formatMoney(e.amount, e.currency)}
                    </Td>
                    <Td $align="right">{formatMoney(e.amount_usd, "USD")}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableScroll>
        )}
      </Card>
    </Stack>
  );
}
