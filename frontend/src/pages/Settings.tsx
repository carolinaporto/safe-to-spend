import { PencilSimple, Plus, TrashSimple } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import styled from "styled-components";

import { DecimalInput } from "../components/DecimalInput";
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
  useDeleteMerchantRule,
  useDeleteRecurringRule,
  useMerchantRules,
  usePeople,
  usePlanConfig,
  useRecurringRules,
  useRunRecurringRule,
  useSaveAccount,
  useSaveCategory,
  useSaveMerchantRule,
  useSavePlanConfig,
  useSaveRecurringRule,
} from "../lib/queries";
import type {
  Account,
  CategoryNature,
  CommittedCost,
  RecurringFrequency,
  RecurringRule,
} from "../lib/types";

const NATURES: CategoryNature[] = [
  "essential",
  "discretionary",
  "setup",
  "fee",
  "income",
];

// Shown next to the nature picker so it's clear which bucket a new category
// belongs in.
const NATURE_HELP: Record<CategoryNature, string> = {
  essential:
    "Must-pay, no real choice — rent, groceries, transport, utilities, health. Counts toward your monthly pace.",
  discretionary:
    "Optional — you could skip it. Restaurants, coffee, clothes, streaming, trips. Counts toward your pace; first thing to cut when money is tight.",
  setup:
    "One-time move-in costs — furniture, deposit, electronics. Tracked, but left OUT of the daily allowance so a big week doesn't wreck the number.",
  fee: "Bank and currency costs — card fees, IOF, FX spread.",
  income:
    "Money coming in — funding, salary/stipend, reimbursements, refunds.",
};

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
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 8.75rem), 1fr));
  gap: ${({ theme }) => theme.space.sm};
  align-items: end;
`;

const CostRow = styled.div`
  display: grid;
  grid-template-columns: 1fr 7.5rem 10rem auto;
  gap: ${({ theme }) => theme.space.sm};
  align-items: center;

  @media (max-width: ${({ theme }) => theme.bp.sm}) {
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

const NatureHint = styled.p`
  grid-column: 1 / -1;
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.textMuted};
  max-width: 62ch;
  margin-top: ${({ theme }) => theme.space.xxs};
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

const BLANK_ACCOUNT = {
  name: "",
  institution: "",
  kind: "checking",
  currency: "USD",
  opening_balance: "0",
  opening_date: today(),
  statement_day: "",
  due_day: "",
  owner_person_id: "",
};

function AccountsSection() {
  const accounts = useAccounts();
  const people = usePeople();
  const save = useSaveAccount();
  const remove = useDeleteAccount();
  const meta = useMeta();
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState(BLANK_ACCOUNT);

  function startEdit(a: Account) {
    setEditingId(a.id);
    setDraft({
      name: a.name,
      institution: a.institution,
      kind: a.kind,
      currency: a.currency,
      opening_balance: a.opening_balance,
      opening_date: a.opening_date.slice(0, 10),
      statement_day: a.statement_day ? String(a.statement_day) : "",
      due_day: a.due_day ? String(a.due_day) : "",
      owner_person_id: a.owner_person_id ? String(a.owner_person_id) : "",
    });
    setError(null);
  }

  function cancelEdit() {
    setEditingId(null);
    setDraft(BLANK_ACCOUNT);
    setError(null);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const body: Record<string, unknown> = {
      name: draft.name,
      institution: draft.institution,
      opening_balance: draft.opening_balance.trim() || "0",
      opening_date: draft.opening_date,
      statement_day: draft.statement_day ? Number(draft.statement_day) : null,
      due_day: draft.due_day ? Number(draft.due_day) : null,
      owner_person_id:
        draft.kind === "external" && draft.owner_person_id
          ? Number(draft.owner_person_id)
          : null,
    };
    try {
      if (editingId !== null) {
        await save.mutateAsync({ id: editingId, ...body });
        cancelEdit();
      } else {
        await save.mutateAsync({
          ...body,
          kind: draft.kind,
          currency: draft.currency,
        });
        setDraft(BLANK_ACCOUNT);
      }
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
                  <Row $gap="xs">
                    <GhostButton
                      type="button"
                      disabled={meta.demo_mode}
                      onClick={() => startEdit(a)}
                      aria-label={`Edit ${a.name}`}
                    >
                      <PencilSimple size={14} />
                    </GhostButton>
                    <GhostButton
                      type="button"
                      disabled={meta.demo_mode}
                      onClick={() => del(a.id)}
                      aria-label={`Delete ${a.name}`}
                    >
                      <TrashSimple size={14} />
                    </GhostButton>
                  </Row>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </TableScroll>

      {editingId !== null && (
        <strong>Editing account #{editingId}</strong>
      )}
      <AddForm onSubmit={submit}>
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
            disabled={editingId !== null}
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
            disabled={editingId !== null}
            onChange={(e) => setDraft({ ...draft, currency: e.target.value })}
          >
            <option value="USD">USD</option>
            <option value="BRL">BRL</option>
          </Select>
        </Field>
        <Field>
          <FieldLabel>Opening balance</FieldLabel>
          <DecimalInput
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
        {draft.kind === "credit_card" && (
          <>
            <Field>
              <FieldLabel>Statement closes (day of month)</FieldLabel>
              <Input
                inputMode="numeric"
                placeholder="e.g. 3"
                value={draft.statement_day}
                onChange={(e) =>
                  setDraft({ ...draft, statement_day: e.target.value })
                }
              />
            </Field>
            <Field>
              <FieldLabel>Payment due (day of month)</FieldLabel>
              <Input
                inputMode="numeric"
                placeholder="e.g. 25"
                value={draft.due_day}
                onChange={(e) =>
                  setDraft({ ...draft, due_day: e.target.value })
                }
              />
            </Field>
          </>
        )}
        {draft.kind === "external" && (
          <Field>
            <FieldLabel>Owner (whose card)</FieldLabel>
            <Select
              value={draft.owner_person_id}
              onChange={(e) =>
                setDraft({ ...draft, owner_person_id: e.target.value })
              }
            >
              <option value="">—</option>
              {(people.data ?? [])
                .filter((p) => p.role !== "me")
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
            </Select>
          </Field>
        )}
        <Button type="submit" disabled={save.isPending}>
          <Plus size={16} />{" "}
          {editingId !== null ? "Save changes" : "Add account"}
        </Button>
        {editingId !== null && (
          <GhostButton type="button" onClick={cancelEdit}>
            Cancel
          </GhostButton>
        )}
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
              <NatureHint>{NATURE_HELP[nature]}</NatureHint>
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
        <NatureHint>
          {NATURE_HELP[draft.nature as CategoryNature]}
        </NatureHint>
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
    if (!form.academic_year_start || !form.academic_year_end) {
      setError("Set both the start and end dates.");
      return;
    }
    try {
      await save.mutateAsync({
        academic_year_start: form.academic_year_start,
        academic_year_end: form.academic_year_end,
        emergency_reserve_usd: form.emergency_reserve_usd.trim() || "0",
        committed_costs: costs.filter(
          (c) => c.label.trim() && c.amount_usd.trim() && c.due_date,
        ),
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
          <DecimalInput
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
              <DecimalInput
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

function MerchantRulesSection() {
  const rules = useMerchantRules();
  const categories = useCategories();
  const save = useSaveMerchantRule();
  const remove = useDeleteMerchantRule();
  const meta = useMeta();
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({
    pattern: "",
    match_type: "contains",
    category_id: "",
    merchant_clean: "",
    priority: "100",
  });

  const catName = new Map(
    (categories.data ?? []).map((c) => [c.id, c.name] as const),
  );

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await save.mutateAsync({
        pattern: draft.pattern,
        match_type: draft.match_type,
        category_id: draft.category_id ? Number(draft.category_id) : null,
        merchant_clean: draft.merchant_clean || null,
        priority: Number(draft.priority) || 100,
      });
      setDraft({ ...draft, pattern: "", merchant_clean: "" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save");
    }
  }

  return (
    <Section>
      <SectionTitle>Merchant rules</SectionTitle>
      <Muted>
        Applied during import (highest priority first) to set a category and a
        clean name from the raw merchant string.
      </Muted>

      <TableScroll>
        <Table>
          <thead>
            <tr>
              <Th>Pattern</Th>
              <Th>Match</Th>
              <Th>Category</Th>
              <Th>Clean name</Th>
              <Th>Priority</Th>
              <Th>Hits</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {(rules.data ?? []).map((r) => (
              <tr key={r.id}>
                <Td>{r.pattern}</Td>
                <Td>{r.match_type}</Td>
                <Td>{r.category_id ? catName.get(r.category_id) : "—"}</Td>
                <Td>{r.merchant_clean || "—"}</Td>
                <Td>{r.priority}</Td>
                <Td>{r.hit_count}</Td>
                <Td>
                  <GhostButton
                    type="button"
                    disabled={meta.demo_mode}
                    aria-label={`Delete rule ${r.pattern}`}
                    onClick={() => remove.mutate(r.id)}
                  >
                    <TrashSimple size={14} />
                  </GhostButton>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </TableScroll>

      {!meta.demo_mode && (
        <AddForm onSubmit={add}>
          <Field>
            <FieldLabel>Pattern</FieldLabel>
            <Input
              required
              value={draft.pattern}
              onChange={(e) => setDraft({ ...draft, pattern: e.target.value })}
            />
          </Field>
          <Field>
            <FieldLabel>Match</FieldLabel>
            <Select
              value={draft.match_type}
              onChange={(e) =>
                setDraft({ ...draft, match_type: e.target.value })
              }
            >
              <option value="contains">contains</option>
              <option value="regex">regex</option>
            </Select>
          </Field>
          <Field>
            <FieldLabel>Category</FieldLabel>
            <Select
              value={draft.category_id}
              onChange={(e) =>
                setDraft({ ...draft, category_id: e.target.value })
              }
            >
              <option value="">—</option>
              {(categories.data ?? [])
                .filter((c) => !c.is_archived)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
            </Select>
          </Field>
          <Field>
            <FieldLabel>Clean name</FieldLabel>
            <Input
              value={draft.merchant_clean}
              onChange={(e) =>
                setDraft({ ...draft, merchant_clean: e.target.value })
              }
            />
          </Field>
          <Field>
            <FieldLabel>Priority</FieldLabel>
            <Input
              inputMode="numeric"
              value={draft.priority}
              onChange={(e) => setDraft({ ...draft, priority: e.target.value })}
            />
          </Field>
          <Button type="submit" disabled={save.isPending}>
            <Plus size={16} /> Add rule
          </Button>
        </AddForm>
      )}
      {error && <ErrorText>{error}</ErrorText>}
    </Section>
  );
}

const FREQUENCIES: RecurringFrequency[] = ["weekly", "monthly", "yearly"];

function RecurringRulesSection() {
  const rules = useRecurringRules();
  const accounts = useAccounts();
  const categories = useCategories();
  const save = useSaveRecurringRule();
  const remove = useDeleteRecurringRule();
  const run = useRunRecurringRule();
  const meta = useMeta();
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState({
    name: "",
    account_id: "",
    category_id: "",
    amount: "",
    currency: "USD",
    frequency: "monthly",
    day_of_month: "1",
    start_date: today(),
    is_income: false,
  });

  const accountName = new Map(
    (accounts.data ?? []).map((a) => [a.id, a.name] as const),
  );
  const catName = new Map(
    (categories.data ?? []).map((c) => [c.id, c.name] as const),
  );

  function startEdit(r: RecurringRule) {
    setEditingId(r.id);
    setDraft({
      name: r.name,
      account_id: String(r.account_id),
      category_id: r.category_id ? String(r.category_id) : "",
      amount: r.amount,
      currency: r.currency,
      frequency: r.frequency,
      day_of_month: String(r.day_of_month),
      start_date: r.start_date.slice(0, 10),
      is_income: r.is_income,
    });
    setError(null);
  }

  function cancelEdit() {
    setEditingId(null);
    setDraft({
      name: "",
      account_id: "",
      category_id: "",
      amount: "",
      currency: "USD",
      frequency: "monthly",
      day_of_month: "1",
      start_date: today(),
      is_income: false,
    });
    setError(null);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const body = {
      name: draft.name,
      account_id: Number(draft.account_id),
      category_id: draft.category_id ? Number(draft.category_id) : null,
      amount: draft.amount,
      currency: draft.currency,
      frequency: draft.frequency,
      day_of_month: Number(draft.day_of_month) || 1,
      start_date: draft.start_date,
      is_income: draft.is_income,
    };
    try {
      if (editingId !== null) {
        await save.mutateAsync({ id: editingId, ...body });
        cancelEdit();
      } else {
        await save.mutateAsync(body);
        setDraft({ ...draft, name: "", amount: "" });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save");
    }
  }

  return (
    <Section>
      <SectionTitle>Recurring rules</SectionTitle>
      <Muted>
        Templates that generate transactions on a schedule. A daily job
        creates any that have come due; “Run now” catches one up immediately.
        Expense rules are reserved from your monthly budget for every month
        left in the plan — edit the amount whenever it changes.
      </Muted>

      <TableScroll>
        <Table>
          <thead>
            <tr>
              <Th>Name</Th>
              <Th>Account</Th>
              <Th>Category</Th>
              <Th $align="right">Amount</Th>
              <Th>Every</Th>
              <Th>Last run</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {(rules.data ?? []).map((r) => (
              <tr key={r.id}>
                <Td>
                  {r.name}
                  {r.is_income ? " (income)" : ""}
                </Td>
                <Td>{accountName.get(r.account_id) ?? "—"}</Td>
                <Td>{r.category_id ? catName.get(r.category_id) : "—"}</Td>
                <Td $align="right">{formatMoney(r.amount, r.currency)}</Td>
                <Td>
                  {r.frequency === "monthly"
                    ? `month · day ${r.day_of_month}`
                    : r.frequency}
                </Td>
                <Td>{r.last_generated_date ?? "never"}</Td>
                <Td>
                  {!meta.demo_mode && (
                    <Row $gap="sm">
                      <GhostButton
                        type="button"
                        aria-label={`Edit ${r.name}`}
                        onClick={() => startEdit(r)}
                      >
                        <PencilSimple size={14} />
                      </GhostButton>
                      <GhostButton
                        type="button"
                        onClick={() => run.mutate(r.id)}
                        disabled={run.isPending}
                      >
                        Run now
                      </GhostButton>
                      <GhostButton
                        type="button"
                        aria-label={`Delete ${r.name}`}
                        onClick={() => remove.mutate(r.id)}
                      >
                        <TrashSimple size={14} />
                      </GhostButton>
                    </Row>
                  )}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </TableScroll>

      {editingId !== null && <strong>Editing rule #{editingId}</strong>}
      {!meta.demo_mode && (
        <AddForm onSubmit={submit}>
          <Field>
            <FieldLabel>Name</FieldLabel>
            <Input
              required
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            />
          </Field>
          <Field>
            <FieldLabel>Account</FieldLabel>
            <Select
              required
              value={draft.account_id}
              onChange={(e) =>
                setDraft({ ...draft, account_id: e.target.value })
              }
            >
              <option value="">Select…</option>
              {(accounts.data ?? []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field>
            <FieldLabel>Category</FieldLabel>
            <Select
              value={draft.category_id}
              onChange={(e) =>
                setDraft({ ...draft, category_id: e.target.value })
              }
            >
              <option value="">—</option>
              {(categories.data ?? [])
                .filter((c) => !c.is_archived)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
            </Select>
          </Field>
          <Field>
            <FieldLabel>Amount</FieldLabel>
            <DecimalInput
              required
              value={draft.amount}
              onChange={(e) => setDraft({ ...draft, amount: e.target.value })}
            />
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
            <FieldLabel>Frequency</FieldLabel>
            <Select
              value={draft.frequency}
              onChange={(e) =>
                setDraft({ ...draft, frequency: e.target.value })
              }
            >
              {FREQUENCIES.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </Select>
          </Field>
          <Field>
            <FieldLabel>Day of month</FieldLabel>
            <Input
              inputMode="numeric"
              value={draft.day_of_month}
              onChange={(e) =>
                setDraft({ ...draft, day_of_month: e.target.value })
              }
            />
          </Field>
          <Field>
            <FieldLabel>Start date</FieldLabel>
            <Input
              type="date"
              value={draft.start_date}
              onChange={(e) =>
                setDraft({ ...draft, start_date: e.target.value })
              }
            />
          </Field>
          <Field>
            <FieldLabel>Kind</FieldLabel>
            <Select
              value={draft.is_income ? "income" : "expense"}
              onChange={(e) =>
                setDraft({ ...draft, is_income: e.target.value === "income" })
              }
            >
              <option value="expense">expense</option>
              <option value="income">income</option>
            </Select>
          </Field>
          <Button type="submit" disabled={save.isPending}>
            <Plus size={16} />{" "}
            {editingId !== null ? "Save changes" : "Add rule"}
          </Button>
          {editingId !== null && (
            <GhostButton type="button" onClick={cancelEdit}>
              Cancel
            </GhostButton>
          )}
        </AddForm>
      )}
      {error && <ErrorText>{error}</ErrorText>}
    </Section>
  );
}

export function Settings() {
  return (
    <Stack $gap="xl">
      <PageTitle>Settings</PageTitle>
      <PlanSection />
      <AccountsSection />
      <RecurringRulesSection />
      <CategoriesSection />
      <MerchantRulesSection />
    </Stack>
  );
}
