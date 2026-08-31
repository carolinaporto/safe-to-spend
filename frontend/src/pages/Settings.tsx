import { Plus, TrashSimple } from "@phosphor-icons/react";
import { useState } from "react";
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
  useSaveAccount,
  useSaveCategory,
} from "../lib/queries";
import { theme } from "../theme";
import type { CategoryNature } from "../lib/types";

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
            <div key={nature}>
              <Muted as="span" style={{ color: theme.nature[nature] }}>
                {nature}
              </Muted>
              <Row $gap="sm" style={{ marginTop: theme.space.sm }}>
                {inNature.map((c) => (
                  <Badge key={c.id} $color={theme.color.text}>
                    <span
                      style={{
                        opacity: c.is_archived ? 0.5 : 1,
                        textDecoration: c.is_archived
                          ? "line-through"
                          : "none",
                      }}
                    >
                      {c.name}
                    </span>
                    <button
                      type="button"
                      aria-label={`Toggle archive ${c.name}`}
                      onClick={() =>
                        save.mutate({
                          id: c.id,
                          is_archived: !c.is_archived,
                        })
                      }
                      style={{
                        background: "none",
                        border: "none",
                        color: theme.color.textMuted,
                        cursor: "pointer",
                      }}
                    >
                      {c.is_archived ? "restore" : "archive"}
                    </button>
                    {!meta.demo_mode && (
                      <button
                        type="button"
                        aria-label={`Delete ${c.name}`}
                        onClick={() => del(c.id)}
                        style={{
                          background: "none",
                          border: "none",
                          color: theme.color.danger,
                          cursor: "pointer",
                        }}
                      >
                        ×
                      </button>
                    )}
                  </Badge>
                ))}
              </Row>
            </div>
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

export function Settings() {
  return (
    <Stack $gap="xl">
      <PageTitle>Settings</PageTitle>
      <Muted>
        Merchant rules, recurring rules, academic-year dates, reserve and
        committed costs arrive in later phases.
      </Muted>
      <AccountsSection />
      <CategoriesSection />
    </Stack>
  );
}
