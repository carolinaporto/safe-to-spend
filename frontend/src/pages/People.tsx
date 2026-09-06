import { HandCoins, Plus, TrashSimple } from "@phosphor-icons/react";
import { useMemo, useState } from "react";
import styled from "styled-components";

import {
  Badge,
  Button,
  Card,
  ErrorText,
  Field,
  FieldLabel,
  GhostButton,
  Input,
  Muted,
  PageTitle,
  Select,
  Stack,
  Table,
  TableScroll,
  Td,
  Th,
} from "../components/ui";
import { ApiError } from "../lib/api";
import { formatMoney } from "../lib/format";
import { useMeta } from "../lib/meta";
import {
  useAccounts,
  useDeletePerson,
  usePeople,
  usePeopleBalances,
  useSavePerson,
  useSettlePerson,
} from "../lib/queries";
import type { PersonRole } from "../lib/types";

const ROLES: PersonRole[] = ["roommate", "parent", "other", "me"];

const SectionTitle = styled.h2`
  font-size: ${({ theme }) => theme.fontSize.lg};
  margin-bottom: ${({ theme }) => theme.space.md};
`;

const BalanceGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 15rem), 1fr));
  gap: ${({ theme }) => theme.space.md};
`;

const BalanceCard = styled(Card)<{ $tone: "inflow" | "outflow" | "muted" }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  border-left: 4px solid
    ${({ theme, $tone }) =>
      $tone === "inflow"
        ? theme.color.inflow
        : $tone === "outflow"
          ? theme.color.outflow
          : theme.color.border};
`;

const NetValue = styled.span<{ $tone: "inflow" | "outflow" | "muted" }>`
  font-size: ${({ theme }) => theme.fontSize.xl};
  font-weight: ${({ theme }) => theme.fontWeight.semibold};
  font-variant-numeric: tabular-nums;
  color: ${({ theme, $tone }) =>
    $tone === "inflow"
      ? theme.color.inflow
      : $tone === "outflow"
        ? theme.color.outflow
        : theme.color.text};
`;

const SettleRow = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  flex-wrap: wrap;
`;

const AddForm = styled.form`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 9.5rem), 1fr));
  gap: ${({ theme }) => theme.space.sm};
  align-items: end;
`;

function tone(net: string): "inflow" | "outflow" | "muted" {
  if (net.startsWith("-")) return "outflow";
  if (Number.parseFloat(net) > 0) return "inflow";
  return "muted";
}

export function People() {
  const people = usePeople();
  const balances = usePeopleBalances();
  const accounts = useAccounts();
  const save = useSavePerson();
  const remove = useDeletePerson();
  const settle = useSettlePerson();
  const meta = useMeta();
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({ name: "", role: "roommate", notes: "" });
  const ownAccounts = (accounts.data ?? []).filter(
    (a) => a.is_owned && a.is_active,
  );
  const [settleAccount, setSettleAccount] = useState<Record<number, string>>({});

  const nameById = useMemo(
    () => new Map((people.data ?? []).map((p) => [p.id, p.name] as const)),
    [people.data],
  );

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await save.mutateAsync({ ...draft });
      setDraft({ ...draft, name: "", notes: "" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save");
    }
  }

  async function doSettle(personId: number) {
    setError(null);
    const accountId = Number(settleAccount[personId] ?? ownAccounts[0]?.id);
    if (!accountId) return;
    try {
      await settle.mutateAsync({ id: personId, account_id: accountId });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not settle");
    }
  }

  return (
    <Stack $gap="xl">
      <PageTitle>People</PageTitle>

      <div>
        <SectionTitle>Who owes whom</SectionTitle>
        {(balances.data ?? []).length === 0 && (
          <Muted>Nothing outstanding — everyone is settled up.</Muted>
        )}
        <BalanceGrid>
          {(balances.data ?? []).map((b) => {
            const t = tone(b.net_usd);
            return (
              <BalanceCard key={b.person_id} $tone={t}>
                <strong>{nameById.get(b.person_id) ?? b.name}</strong>
                <NetValue $tone={t}>
                  {t === "outflow"
                    ? `You owe ${formatMoney(b.i_owe_usd, "USD")}`
                    : t === "inflow"
                      ? `Owes you ${formatMoney(b.owed_to_me_usd, "USD")}`
                      : "Settled"}
                </NetValue>
                {t !== "muted" && (
                  <Muted>
                    owed to you {formatMoney(b.owed_to_me_usd, "USD")} · you owe{" "}
                    {formatMoney(b.i_owe_usd, "USD")}
                  </Muted>
                )}
                {!meta.demo_mode && t !== "muted" && (
                  <SettleRow>
                    <Select
                      aria-label="Settle into account"
                      value={
                        settleAccount[b.person_id] ??
                        String(ownAccounts[0]?.id ?? "")
                      }
                      onChange={(e) =>
                        setSettleAccount({
                          ...settleAccount,
                          [b.person_id]: e.target.value,
                        })
                      }
                    >
                      {ownAccounts.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                    </Select>
                    <Button
                      type="button"
                      disabled={settle.isPending}
                      onClick={() => doSettle(b.person_id)}
                    >
                      <HandCoins size={16} /> Mark settled
                    </Button>
                  </SettleRow>
                )}
              </BalanceCard>
            );
          })}
        </BalanceGrid>
        {error && <ErrorText>{error}</ErrorText>}
      </div>

      <Card>
        <SectionTitle>People</SectionTitle>
        <TableScroll>
          <Table>
            <thead>
              <tr>
                <Th>Name</Th>
                <Th>Role</Th>
                <Th>Notes</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {(people.data ?? []).map((p) => (
                <tr key={p.id}>
                  <Td>{p.name}</Td>
                  <Td>
                    <Badge>{p.role}</Badge>
                  </Td>
                  <Td>{p.notes || "—"}</Td>
                  <Td>
                    {!meta.demo_mode && p.role !== "me" && (
                      <GhostButton
                        type="button"
                        aria-label={`Delete ${p.name}`}
                        onClick={() => remove.mutate(p.id)}
                      >
                        <TrashSimple size={14} />
                      </GhostButton>
                    )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </TableScroll>

        {!meta.demo_mode && (
          <AddForm onSubmit={add}>
            <Field>
              <FieldLabel>Name</FieldLabel>
              <Input
                required
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              />
            </Field>
            <Field>
              <FieldLabel>Role</FieldLabel>
              <Select
                value={draft.role}
                onChange={(e) => setDraft({ ...draft, role: e.target.value })}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </Select>
            </Field>
            <Field>
              <FieldLabel>Notes</FieldLabel>
              <Input
                value={draft.notes}
                onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
              />
            </Field>
            <Button type="submit" disabled={save.isPending}>
              <Plus size={16} /> Add person
            </Button>
          </AddForm>
        )}
      </Card>
    </Stack>
  );
}
