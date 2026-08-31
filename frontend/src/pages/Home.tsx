import styled from "styled-components";

import { Card, Muted, PageTitle, Stack } from "../components/ui";
import { formatMoney } from "../lib/format";
import { useDashboardBalances } from "../lib/queries";

const HeroCard = styled(Card)`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
`;

const HeroLabel = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

const HeroValue = styled.span<{ $negative: boolean }>`
  font-size: ${({ theme }) => theme.fontSize.display};
  font-weight: ${({ theme }) => theme.fontWeight.bold};
  font-variant-numeric: tabular-nums;
  color: ${({ theme, $negative }) =>
    $negative ? theme.color.danger : theme.color.text};
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: ${({ theme }) => theme.space.lg};
`;

const AccountCard = styled(Card)`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

const AccountName = styled.div`
  font-weight: ${({ theme }) => theme.fontWeight.semibold};
`;

const Balances = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: ${({ theme }) => theme.space.md};
  font-variant-numeric: tabular-nums;
`;

const Native = styled.span`
  font-size: ${({ theme }) => theme.fontSize.lg};
`;

const Usd = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export function Home() {
  const { data, isLoading, isError } = useDashboardBalances();

  if (isLoading) return <Muted>Loading balances…</Muted>;
  if (isError || !data) return <Muted>Could not load balances.</Muted>;

  return (
    <Stack $gap="xl">
      <PageTitle>Home</PageTitle>

      <HeroCard>
        <HeroLabel>Net worth (owned accounts, USD)</HeroLabel>
        <HeroValue $negative={data.net_worth_usd.startsWith("-")}>
          {formatMoney(data.net_worth_usd, "USD")}
        </HeroValue>
        <Muted>
          The full dashboard — daily allowance, runway, projections — arrives in
          Phase 2.
        </Muted>
      </HeroCard>

      <Grid>
        {data.accounts.map((account) => (
          <AccountCard key={account.id}>
            <AccountName>{account.name}</AccountName>
            <Muted as="span">
              {account.institution} · {account.kind.replace("_", " ")}
            </Muted>
            <Balances>
              <Native>{formatMoney(account.balance, account.currency)}</Native>
              {account.currency !== "USD" && (
                <Usd>≈ {formatMoney(account.balance_usd, "USD")}</Usd>
              )}
            </Balances>
          </AccountCard>
        ))}
      </Grid>
    </Stack>
  );
}
