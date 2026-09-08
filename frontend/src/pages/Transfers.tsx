import {
  ArrowRight,
  PencilSimple,
  Plus,
  TrashSimple,
} from "@phosphor-icons/react";
import { useMemo, useState } from "react";
import styled from "styled-components";

import { ProviderRateChart, TransferCostChart } from "../components/charts";
import { DecimalInput } from "../components/DecimalInput";
import {
  Button,
  Card,
  ErrorText,
  Field,
  FieldLabel,
  GhostButton,
  Input,
  Muted,
  PageTitle,
  Row,
  Select,
  Stack,
  Table,
  TableScroll,
  Td,
  Th,
} from "../components/ui";
import { ApiError } from "../lib/api";
import { formatDate, formatMoney } from "../lib/format";
import { useMeta } from "../lib/meta";
import {
  useAccounts,
  useCreateTransfer,
  useDeleteTransfer,
  useTransfers,
  useTransferSummary,
  useUpdateTransfer,
} from "../lib/queries";
import type { Transfer } from "../lib/types";

const today = () => new Date().toISOString().slice(0, 10);

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
  gap: ${({ theme }) => theme.space.lg};
`;

const FormGrid = styled.form`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 9.5rem), 1fr));
  gap: ${({ theme }) => theme.space.md};
  align-items: end;
`;

const SectionTitle = styled.h2`
  font-size: ${({ theme }) => theme.fontSize.lg};
  margin-bottom: ${({ theme }) => theme.space.md};
`;

const Stat = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xxs};
`;

const StatValue = styled.span`
  font-size: ${({ theme }) => theme.fontSize.xl};
  font-weight: ${({ theme }) => theme.fontWeight.semibold};
  font-variant-numeric: tabular-nums;
`;

const emptyDraft = {
  from_account_id: "",
  to_account_id: "",
  amount_out: "",
  amount_in: "",
  market_rate: "",
  provider: "",
  date: today(),
};

export function Transfers() {
  const accounts = useAccounts();
  const transfers = useTransfers();
  const summary = useTransferSummary();
  const create = useCreateTransfer();
  const update = useUpdateTransfer();
  const remove = useDeleteTransfer();
  const meta = useMeta();
  const [draft, setDraft] = useState(emptyDraft);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  function editTransfer(t: Transfer) {
    setEditingId(t.id);
    setDraft({
      from_account_id: String(t.from_account_id),
      to_account_id: String(t.to_account_id),
      amount_out: t.amount_out,
      amount_in: t.amount_in,
      market_rate: "",
      provider: t.provider,
      date: t.date.slice(0, 10),
    });
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEdit() {
    setEditingId(null);
    setDraft(emptyDraft);
    setError(null);
  }

  const accountName = useMemo(
    () => new Map((accounts.data ?? []).map((a) => [a.id, a] as const)),
    [accounts.data],
  );

  const preview = useMemo(() => {
    const out = Number.parseFloat(draft.amount_out);
    const inn = Number.parseFloat(draft.amount_in);
    if (!out || !inn) return null;
    return (inn / out).toFixed(6);
  }, [draft.amount_out, draft.amount_in]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const body = {
      date: draft.date,
      from_account_id: Number(draft.from_account_id),
      to_account_id: Number(draft.to_account_id),
      amount_out: draft.amount_out,
      amount_in: draft.amount_in,
      provider: draft.provider,
      ...(draft.market_rate ? { market_rate: draft.market_rate } : {}),
    };
    try {
      if (editingId !== null) {
        await update.mutateAsync({ id: editingId, ...body });
        cancelEdit();
      } else {
        await create.mutateAsync(body);
        setDraft({ ...emptyDraft, date: draft.date, provider: draft.provider });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save transfer");
    }
  }

  const activeAccounts = (accounts.data ?? []).filter(
    (a) => a.is_owned && a.is_active,
  );

  return (
    <Stack $gap="xl">
      <PageTitle>Transfers</PageTitle>

      <Grid>
        <Card>
          <Stat>
            <Muted>Cumulative FX cost</Muted>
            <StatValue>
              {formatMoney(summary.data?.total_fx_cost_usd ?? "0", "USD")}
            </StatValue>
            <Muted>
              across {summary.data?.count ?? 0} transfer
              {summary.data?.count === 1 ? "" : "s"} — what the spread and fees
              have cost you versus the mid-market rate
            </Muted>
          </Stat>
        </Card>
        <Card>
          <SectionTitle>Cost over time</SectionTitle>
          {transfers.data && (
            <TransferCostChart transfers={transfers.data} />
          )}
        </Card>
      </Grid>

      {summary.data && summary.data.providers.length > 0 && (
        <Card>
          <SectionTitle>Effective rate by provider</SectionTitle>
          <ProviderRateChart providers={summary.data.providers} />
          <TableScroll>
            <Table>
              <thead>
                <tr>
                  <Th>Provider</Th>
                  <Th $align="right">Transfers</Th>
                  <Th $align="right">Avg effective rate</Th>
                  <Th $align="right">FX cost</Th>
                </tr>
              </thead>
              <tbody>
                {summary.data.providers.map((p) => (
                  <tr key={p.provider}>
                    <Td>{p.provider}</Td>
                    <Td $align="right">{p.count}</Td>
                    <Td $align="right">{p.avg_effective_rate}</Td>
                    <Td $align="right">
                      {formatMoney(p.fx_cost_usd, "USD")}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableScroll>
        </Card>
      )}

      {!meta.demo_mode && (
        <Card>
          <SectionTitle>
            {editingId !== null
              ? `Edit transfer #${editingId}`
              : "Log a transfer"}
          </SectionTitle>
          <FormGrid onSubmit={submit}>
            <Field>
              <FieldLabel>From</FieldLabel>
              <Select
                required
                value={draft.from_account_id}
                onChange={(e) =>
                  setDraft({ ...draft, from_account_id: e.target.value })
                }
              >
                <option value="">Select…</option>
                {activeAccounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} ({a.currency})
                  </option>
                ))}
              </Select>
            </Field>
            <Field>
              <FieldLabel>To</FieldLabel>
              <Select
                required
                value={draft.to_account_id}
                onChange={(e) =>
                  setDraft({ ...draft, to_account_id: e.target.value })
                }
              >
                <option value="">Select…</option>
                {activeAccounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} ({a.currency})
                  </option>
                ))}
              </Select>
            </Field>
            <Field>
              <FieldLabel>Amount out</FieldLabel>
              <DecimalInput
                required
                value={draft.amount_out}
                onChange={(e) =>
                  setDraft({ ...draft, amount_out: e.target.value })
                }
              />
            </Field>
            <Field>
              <FieldLabel>Amount in</FieldLabel>
              <DecimalInput
                required
                value={draft.amount_in}
                onChange={(e) =>
                  setDraft({ ...draft, amount_in: e.target.value })
                }
              />
            </Field>
            <Field>
              <FieldLabel>Market rate (optional)</FieldLabel>
              <DecimalInput
                placeholder="mid-market"
                value={draft.market_rate}
                onChange={(e) =>
                  setDraft({ ...draft, market_rate: e.target.value })
                }
              />
            </Field>
            <Field>
              <FieldLabel>Provider</FieldLabel>
              <Input
                value={draft.provider}
                onChange={(e) =>
                  setDraft({ ...draft, provider: e.target.value })
                }
              />
            </Field>
            <Field>
              <FieldLabel>Date</FieldLabel>
              <Input
                type="date"
                value={draft.date}
                onChange={(e) => setDraft({ ...draft, date: e.target.value })}
              />
            </Field>
            <Button
              type="submit"
              disabled={create.isPending || update.isPending}
            >
              <Plus size={16} />{" "}
              {editingId !== null ? "Save changes" : "Add transfer"}
            </Button>
            {editingId !== null && (
              <GhostButton type="button" onClick={cancelEdit}>
                Cancel
              </GhostButton>
            )}
          </FormGrid>
          {preview && (
            <Muted>Effective rate ≈ {preview} (amount in ÷ amount out)</Muted>
          )}
          {error && <ErrorText>{error}</ErrorText>}
        </Card>
      )}

      <Card>
        <SectionTitle>History</SectionTitle>
        <TableScroll>
          <Table>
            <thead>
              <tr>
                <Th>Date</Th>
                <Th>Route</Th>
                <Th $align="right">Out</Th>
                <Th $align="right">In</Th>
                <Th $align="right">Effective</Th>
                <Th $align="right">Market</Th>
                <Th $align="right">FX cost</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {(transfers.data ?? []).map((t) => (
                <tr key={t.id}>
                  <Td>{formatDate(t.date)}</Td>
                  <Td>
                    {accountName.get(t.from_account_id)?.name ?? "?"}{" "}
                    <ArrowRight size={12} />{" "}
                    {accountName.get(t.to_account_id)?.name ?? "?"}
                    {t.provider ? ` · ${t.provider}` : ""}
                  </Td>
                  <Td $align="right">
                    {formatMoney(t.amount_out, t.currency_out)}
                  </Td>
                  <Td $align="right">
                    {formatMoney(t.amount_in, t.currency_in)}
                  </Td>
                  <Td $align="right">{t.effective_rate}</Td>
                  <Td $align="right">{t.market_rate}</Td>
                  <Td $align="right">{formatMoney(t.fx_cost_usd, "USD")}</Td>
                  <Td $align="right">
                    {!meta.demo_mode && (
                      <Row $gap="xs">
                        <GhostButton
                          type="button"
                          aria-label="Edit transfer"
                          onClick={() => editTransfer(t)}
                        >
                          <PencilSimple size={14} />
                        </GhostButton>
                        <GhostButton
                          type="button"
                          aria-label="Delete transfer"
                          onClick={() => {
                            if (window.confirm("Delete this transfer?"))
                              remove.mutate(t.id);
                          }}
                        >
                          <TrashSimple size={14} />
                        </GhostButton>
                      </Row>
                    )}
                  </Td>
                </tr>
              ))}
              {(transfers.data ?? []).length === 0 && (
                <tr>
                  <Td colSpan={8}>
                    <Muted>No transfers logged yet.</Muted>
                  </Td>
                </tr>
              )}
            </tbody>
          </Table>
        </TableScroll>
      </Card>
    </Stack>
  );
}
