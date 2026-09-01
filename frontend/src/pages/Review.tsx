import { CheckCircle } from "@phosphor-icons/react";
import { useMemo } from "react";
import styled from "styled-components";

import {
  Badge,
  Card,
  GhostButton,
  Muted,
  PageTitle,
  Row,
  Select,
  Stack,
} from "../components/ui";
import { formatDate, formatMoney } from "../lib/format";
import {
  useAccounts,
  useCategories,
  useReviewQueue,
  useUpdateTransaction,
} from "../lib/queries";

const Item = styled(Card)`
  display: grid;
  grid-template-columns: 1fr auto;
  gap: ${({ theme }) => theme.space.md};
  align-items: center;

  @media (max-width: 560px) {
    grid-template-columns: 1fr;
  }
`;

const Meta = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xxs};
`;

const Amount = styled.span<{ $in: boolean }>`
  font-variant-numeric: tabular-nums;
  font-weight: ${({ theme }) => theme.fontWeight.semibold};
  color: ${({ theme, $in }) => ($in ? theme.color.inflow : theme.color.text)};
`;

const Actions = styled(Row)`
  gap: ${({ theme }) => theme.space.sm};
`;

const Empty = styled(Card)`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  color: ${({ theme }) => theme.color.success};
`;

export function Review() {
  const queue = useReviewQueue();
  const accounts = useAccounts();
  const categories = useCategories();
  const update = useUpdateTransaction();

  const accountName = useMemo(() => {
    const m = new Map<number, string>();
    (accounts.data ?? []).forEach((a) => m.set(a.id, a.name));
    return m;
  }, [accounts.data]);

  const active = (categories.data ?? []).filter((c) => !c.is_archived);
  const items = queue.data?.items ?? [];

  function resolve(id: number, categoryId: number | null) {
    update.mutate({ id, category_id: categoryId, needs_review: false });
  }

  if (queue.isLoading) return <Muted>Loading…</Muted>;

  return (
    <Stack $gap="lg">
      <PageTitle>Review</PageTitle>

      {items.length === 0 ? (
        <Empty>
          <CheckCircle size={18} weight="fill" />
          Nothing to review — every transaction is categorised.
        </Empty>
      ) : (
        <>
          <Muted>
            {queue.data?.total} transaction
            {queue.data?.total === 1 ? "" : "s"} need a category or a rate check.
          </Muted>
          {items.map((t) => (
            <Item key={t.id}>
              <Meta>
                <Row $gap="sm">
                  <strong>
                    {t.merchant_clean || t.merchant_raw || t.description || "—"}
                  </strong>
                  <Badge>{t.source}</Badge>
                </Row>
                <Muted as="span">
                  {formatDate(t.date)} · {accountName.get(t.account_id) ?? "—"} ·{" "}
                  <Amount $in={t.direction === "in"}>
                    {t.direction === "in" ? "+" : "−"}
                    {formatMoney(t.amount, t.currency)}
                  </Amount>
                  {t.currency !== "USD" && (
                    <> (≈ {formatMoney(t.amount_usd, "USD")})</>
                  )}
                </Muted>
              </Meta>
              <Actions>
                <Select
                  aria-label={`Category for ${t.merchant_raw ?? t.id}`}
                  defaultValue={t.category_id ?? ""}
                  onChange={(e) =>
                    resolve(t.id, e.target.value ? Number(e.target.value) : null)
                  }
                >
                  <option value="">Pick a category…</option>
                  {active.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </Select>
                <GhostButton
                  type="button"
                  onClick={() => resolve(t.id, t.category_id)}
                >
                  Looks fine
                </GhostButton>
              </Actions>
            </Item>
          ))}
        </>
      )}
    </Stack>
  );
}
