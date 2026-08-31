import { Plus, TrashSimple } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
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
  Row,
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
  useCategories,
  useDeleteAccount,
  useDeleteCategory,
  usePlanConfig,
  useSaveAccount,
  useSaveCategory,
  useSavePlanConfig,
} from "../lib/queries";
import type { CategoryNature, CommittedCost } from "../lib/types";

const NATURES: CategoryNature[] = [
  "essential",
  "discretionary",
  "setup",
  "fee",
  "income",
];

const Section = styled(Card)`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

const SectionTitle = styled.h2`
  font-size: ${({ theme }) => theme.fontSize.lg};
`;

const AddForm = styled.form`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: ${({ theme }) => theme.space.sm};
  align-items: end;
`;

const CostRow = styled.div`
  display: grid;
  grid-template-columns: 1fr 120px 160px auto;
  gap: ${({ theme }) => theme.space.sm};
  align-items: center;

  @media (max-width: 720px) {
    grid-template-columns: 1fr 1fr;
  }
`;

const NatureGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

const NatureLabel = styled.span<{ $nature: CategoryNature }>`
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: ${({ theme }) => theme.fontWeight.medium};
  text-transform: capitalize;
  color: ${({ theme, $nature }) => theme.nature[$nature]};
`;

const CategoryName = styled.span<{ $archived: boolean }>`
  opacity: ${({ $archived }) => ($archived ? 0.5 : 1)};
  text-decoration: ${({ $archived }) =>
    $archived ? "line-through" : "none"};
`;

const ChipButton = styled.button<{ $danger?: boolean }>`
  background: none;
  border: none;
  cursor: pointer;
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme, $danger }) =>
    $danger ? theme.color.danger : theme.color.textMuted};

  &:hover {
    color: ${({ theme, $danger }) =>
      $danger ? theme.color.danger : theme.color.text};
  }
`;

const today = () => new Date().toISOString().slice(0, 10);

function AccountsSection() {
  const accounts = useAccounts();
  const save = useSaveAccount();
  const remove = useDeleteAccount();
  const meta = useMeta();
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({
    name: "",
    institution: "",
    kind: "checking",
    currency: "USD",
    opening_balance: "0",
    opening_date: today(),
  });

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await save.mutateAsync({ ...draft });
      setDraft({ ...draft, name: "", institution: "", opening_balance: "0" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save");
    }
  }

  async function del(id: number) {
    setError(null);
    try {
      await remove.mutateAsync(id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete");
    }
  }

  return (
    <Section>
      <SectionTitle>Accounts</SectionTitle>

      <TableScroll>
        <Table>
          <thead>
            <tr>
              <Th>Name</Th>
              <Th>Institution</Th>
              <Th>Kind</Th>
              <Th>Currency</Th>
              <Th>Balance</Th>
              <Th>Active</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {(accounts.data ?? []).map((a) => (
              <tr key={a.id}>
                <Td>{a.name}</Td>
                <Td>{a.institution || "—"}</Td>
                <Td>{a.kind.replace("_", " ")}</Td>
                <Td>{a.currency}</Td>
                <Td>{formatMoney(a.balance, a.currency)}</Td>
                <Td>
                  <input
                    type="checkbox"
                    aria-label={`${a.name} active`}
                    checked={a.is_active}
                    onChange={(e) =>
                      save.mutate({ id: a.id, is_active: e.target.checked })
                    }
                  />
                </Td>
                <Td>
                  <GhostButton
                    type="button"
                    disabled={meta.demo_mode}
                    onClick={() => del(a.id)}
                    aria-label={`Delete ${a.name}`}
                  >
                    <TrashSimple size={14} />
                  </GhostButton>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </TableScroll>

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
          <FieldLabel>Institution</FieldLabel>
          <Input
            value={draft.institution}
            onChange={(e) =>
              setDraft({ ...draft, institution: e.target.value })
            }
          />
        </Field>
        <Field>
          <FieldLabel>Kind</FieldLabel>
          <Select
            value={draft.kind}
            onChange={(e) => setDraft({ ...draft, kind: e.target.value })}
          >
            {["checking", "savings", "credit_card", "cash", "external"].map(
              (k) => (
                <option key={k} value={k}>
                  {k.replace("_", " ")}
                </option>
              ),
            )}
          </Select>
        </Field>
        <Field>
          <FieldLabel>Currency</FieldLabel>
          <Select
            value={draft.currency}
            onChange={(e) => setDraft({ ...draft, currency: e.target.value })}
          >
            <option value="USD">USD</option>
            <option value="BRL">BRL</option>
          </Select>
        </Field>
        <Field>
          <FieldLabel>Opening balance</FieldLabel>
          <Input
            inputMode="decimal"
            value={draft.opening_balance}
            onChange={(e) =>
              setDraft({ ...draft, opening_balance: e.target.value })
            }
          />
        </Field>
        <Field>
          <FieldLabel>Opening date</FieldLabel>
          <Input
            type="date"
            value={draft.opening_date}
            onChange={(e) =>
              setDraft({ ...draft, opening_date: e.target.value })
            }
          />
        </Field>
        <Button type="submit" disabled={save.isPending}>
          <Plus size={16} /> Add account
        </Button>
      </AddForm>
      {error && <ErrorText>{error}</ErrorText>}
    </Section>
  );
}

function CategoriesSection() {
  const categories = useCategories();
  const save = useSaveCategory();
  const remove = useDeleteCategory();
  const meta = useMeta();
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({ name: "", nature: "essential" });

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await save.mutateAsync({ ...draft });
      setDraft({ ...draft, name: "" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save");
    }
  }

  async function del(id: number) {
    setError(null);
    try {
      await remove.mutateAsync(id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete");
    }
  }

  return (
    <Section>
      <SectionTitle>Categories</SectionTitle>
      <Stack $gap="md">
        {NATURES.map((nature) => {
          const inNature = (categories.data ?? []).filter(
            (c) => c.nature === nature,
          );
          if (inNature.length === 0) return null;
          return (
            <NatureGroup key={nature}>
              <NatureLabel $nature={nature}>{nature}</NatureLabel>
              <Row $gap="sm">
                {inNature.map((c) => (
                  <Badge key={c.id}>
                    <CategoryName $archived={c.is_archived}>
                      {c.name}
                    </CategoryName>
                    <ChipButton
                      type="button"
                      aria-label={`Toggle archive ${c.name}`}
                      onClick={() =>
                        save.mutate({
                          id: c.id,
                          is_archived: !c.is_archived,
                        })
                      }
                    >
                      {c.is_archived ? "restore" : "archive"}
                    </ChipButton>
                    {!meta.demo_mode && (
                      <ChipButton
                        type="button"
                        $danger
                        aria-label={`Delete ${c.name}`}
                        onClick={() => del(c.id)}
                      >
                        ×
                      </ChipButton>
                    )}
                  </Badge>
                ))}
              </Row>
            </NatureGroup>
          );
        })}
      </Stack>

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
          <FieldLabel>Nature</FieldLabel>
          <Select
            value={draft.nature}
            onChange={(e) => setDraft({ ...draft, nature: e.target.value })}
          >
            {NATURES.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </Select>
        </Field>
        <Button type="submit" disabled={save.isPending}>
          <Plus size={16} /> Add category
        </Button>
      </AddForm>
      {error && <ErrorText>{error}</ErrorText>}
    </Section>
  );
}

function PlanSection() {
  const { data } = usePlanConfig();
  const save = useSavePlanConfig();
  const meta = useMeta();
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    academic_year_start: "",
    academic_year_end: "",
    emergency_reserve_usd: "",
  });
  const [costs, setCosts] = useState<CommittedCost[]>([]);

  useEffect(() => {
    if (!data) return;
    setForm({
      academic_year_start: data.academic_year_start,
      academic_year_end: data.academic_year_end,
      emergency_reserve_usd: data.emergency_reserve_usd,
    });
    setCosts(data.committed_costs);
  }, [data]);

  async function persist(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await save.mutateAsync({
        ...form,
        committed_costs: costs.filter((c) => c.label && c.amount_usd),
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save");
    }
  }

  if (!data) return null;

  return (
    <Section as="form" onSubmit={persist}>
      <SectionTitle>Plan</SectionTitle>
      <AddForm as="div">
        <Field>
          <FieldLabel>Academic year start</FieldLabel>
          <Input
            type="date"
            disabled={meta.demo_mode}
            value={form.academic_year_start}
            onChange={(e) =>
              setForm({ ...form, academic_year_start: e.target.value })
            }
          />
        </Field>
        <Field>
          <FieldLabel>Academic year end</FieldLabel>
          <Input
            type="date"
            disabled={meta.demo_mode}
            value={form.academic_year_end}
            onChange={(e) =>
              setForm({ ...form, academic_year_end: e.target.value })
            }
          />
        </Field>
        <Field>
          <FieldLabel>Emergency reserve (USD)</FieldLabel>
          <Input
            inputMode="decimal"
            disabled={meta.demo_mode}
            value={form.emergency_reserve_usd}
            onChange={(e) =>
              setForm({ ...form, emergency_reserve_usd: e.target.value })
            }
          />
        </Field>
      </AddForm>

      <div>
        <FieldLabel>Future committed costs</FieldLabel>
        <Stack $gap="sm">
          {costs.map((cost, i) => (
            <CostRow key={i}>
              <Input
                placeholder="Label"
                disabled={meta.demo_mode}
                value={cost.label}
                onChange={(e) =>
                  setCosts(
                    costs.map((c, j) =>
                      j === i ? { ...c, label: e.target.value } : c,
                    ),
                  )
                }
              />
              <Input
                inputMode="decimal"
                placeholder="USD"
                disabled={meta.demo_mode}
                value={cost.amount_usd}
                onChange={(e) =>
                  setCosts(
                    costs.map((c, j) =>
                      j === i ? { ...c, amount_usd: e.target.value } : c,
                    ),
                  )
                }
              />
              <Input
                type="date"
                disabled={meta.demo_mode}
                value={cost.due_date}
                onChange={(e) =>
                  setCosts(
                    costs.map((c, j) =>
                      j === i ? { ...c, due_date: e.target.value } : c,
                    ),
                  )
                }
              />
              {!meta.demo_mode && (
                <GhostButton
                  type="button"
                  aria-label="Remove cost"
                  onClick={() => setCosts(costs.filter((_, j) => j !== i))}
                >
                  <TrashSimple size={14} />
                </GhostButton>
              )}
            </CostRow>
          ))}
          {!meta.demo_mode && (
            <GhostButton
              type="button"
              onClick={() =>
                setCosts([
                  ...costs,
                  { label: "", amount_usd: "", due_date: form.academic_year_end },
                ])
              }
            >
              <Plus size={14} /> Add committed cost
            </GhostButton>
          )}
        </Stack>
      </div>

      {error && <ErrorText>{error}</ErrorText>}
      {!meta.demo_mode && (
        <Row>
          <Button type="submit" disabled={save.isPending}>
            Save plan
          </Button>
        </Row>
      )}
    </Section>
  );
}

export function Settings() {
  return (
    <Stack $gap="xl">
      <PageTitle>Settings</PageTitle>
      <Muted>
        Merchant rules and recurring rules arrive in later phases.
      </Muted>
      <PlanSection />
      <AccountsSection />
      <CategoriesSection />
    </Stack>
  );
}
