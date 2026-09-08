import {
  ArrowsLeftRight,
  DownloadSimple,
  PencilSimple,
  TrashSimple,
  Warning,
} from "@phosphor-icons/react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
  type RowSelectionState,
} from "@tanstack/react-table";
import { useCallback, useMemo, useState } from "react";
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
import { ApiError, getToken } from "../lib/api";
import { formatDate, formatMoney } from "../lib/format";
import { useMeta } from "../lib/meta";
import {
  filtersToParams,
  suggestRule,
  useAccounts,
  useBulkCategorize,
  useCategories,
  useDeleteTransaction,
  useSaveMerchantRule,
  useTransactions,
  useUpdateTransaction,
  type TransactionFilters,
} from "../lib/queries";
import type { Theme } from "../theme";
import type { Category, Transaction } from "../lib/types";

const Filters = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 9.5rem), 1fr));
  gap: ${({ theme }) => theme.space.sm};
`;

const Bar = styled(Row)`
  justify-content: space-between;
`;

const InlineSelect = styled(Select)`
  padding: ${({ theme }) => `${theme.space.xxs} ${theme.space.xs}`};
  font-size: ${({ theme }) => theme.fontSize.xs};
  max-width: 11rem;
`;

const CategorySelect = styled(InlineSelect)<{ $nature?: keyof Theme["nature"] }>`
  color: ${({ theme, $nature }) =>
    $nature ? theme.nature[$nature] : theme.color.text};
`;

const Amount = styled.span<{ $in: boolean }>`
  font-variant-numeric: tabular-nums;
  color: ${({ theme, $in }) => ($in ? theme.color.inflow : theme.color.text)};
`;

const ReviewBadge = styled(Badge)`
  color: ${({ theme }) => theme.color.warning};
  margin-left: ${({ theme }) => theme.space.xs};
`;

const RightTh = styled(Th)`
  text-align: right;
`;

const RightTd = styled(Td)`
  text-align: right;
`;

const RulePrompt = styled(Card)`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  flex-wrap: wrap;
  border-left: 3px solid ${({ theme }) => theme.color.primary};
`;

const emptyFilters: TransactionFilters = { page: 1, page_size: 50 };

const column = createColumnHelper<Transaction>();

const EditCard = styled(Card)`
  border-left: 3px solid ${({ theme }) => theme.color.primary};
`;

const EditGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 9.5rem), 1fr));
  gap: ${({ theme }) => theme.space.md};
`;

const MANUAL_KINDS = ["expense", "income", "adjustment"] as const;

function EditTransactionPanel({
  txn,
  categories,
  onClose,
}: {
  txn: Transaction;
  categories: Category[];
  onClose: () => void;
}) {
  const accounts = useAccounts();
  const update = useUpdateTransaction();
  const del = useDeleteTransaction();
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    date: txn.date.slice(0, 10),
    account_id: String(txn.account_id),
    kind: txn.kind,
    direction: txn.direction,
    amount: txn.amount,
    category_id: txn.category_id ? String(txn.category_id) : "",
    merchant_clean: txn.merchant_clean ?? "",
    description: txn.description,
    notes: txn.notes,
  });

  function set<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await update.mutateAsync({
        id: txn.id,
        date: form.date,
        account_id: Number(form.account_id),
        kind: form.kind,
        direction: form.kind === "adjustment" ? form.direction : undefined,
        amount: form.amount,
        category_id: form.category_id ? Number(form.category_id) : null,
        merchant_clean: form.merchant_clean || null,
        description: form.description,
        notes: form.notes,
      });
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save");
    }
  }

  async function remove() {
    if (!window.confirm("Delete this transaction? This can't be undone.")) return;
    setError(null);
    try {
      await del.mutateAsync(txn.id);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete");
    }
  }

  return (
    <EditCard as="form" onSubmit={save}>
      <Stack $gap="md">
        <Row $gap="sm">
          <strong>Edit transaction #{txn.id}</strong>
          <Muted as="span">— balances recompute automatically on save</Muted>
        </Row>
        <EditGrid>
          <Field>
            <FieldLabel>Date</FieldLabel>
            <Input
              type="date"
              value={form.date}
              onChange={(e) => set("date", e.target.value)}
            />
          </Field>
          <Field>
            <FieldLabel>Account</FieldLabel>
            <Select
              value={form.account_id}
              onChange={(e) => set("account_id", e.target.value)}
            >
              {(accounts.data ?? []).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.currency})
                </option>
              ))}
            </Select>
          </Field>
          <Field>
            <FieldLabel>Kind</FieldLabel>
            <Select
              value={form.kind}
              onChange={(e) =>
                set("kind", e.target.value as Transaction["kind"])
              }
            >
              {MANUAL_KINDS.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </Select>
          </Field>
          {form.kind === "adjustment" && (
            <Field>
              <FieldLabel>Direction</FieldLabel>
              <Select
                value={form.direction}
                onChange={(e) =>
                  set("direction", e.target.value as Transaction["direction"])
                }
              >
                <option value="out">out (money leaves)</option>
                <option value="in">in (money arrives)</option>
              </Select>
            </Field>
          )}
          <Field>
            <FieldLabel>Amount ({txn.currency})</FieldLabel>
            <DecimalInput
              value={form.amount}
              onChange={(e) => set("amount", e.target.value)}
            />
          </Field>
          <Field>
            <FieldLabel>Category</FieldLabel>
            <Select
              value={form.category_id}
              onChange={(e) => set("category_id", e.target.value)}
            >
              <option value="">Uncategorized</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field>
            <FieldLabel>Merchant</FieldLabel>
            <Input
              value={form.merchant_clean}
              onChange={(e) => set("merchant_clean", e.target.value)}
            />
          </Field>
          <Field>
            <FieldLabel>Note</FieldLabel>
            <Input
              value={form.notes}
              onChange={(e) => set("notes", e.target.value)}
            />
          </Field>
        </EditGrid>
        {error && <ErrorText>{error}</ErrorText>}
        <Row $gap="sm">
          <Button type="submit" disabled={update.isPending}>
            Save changes
          </Button>
          <GhostButton type="button" onClick={onClose}>
            Cancel
          </GhostButton>
          <GhostButton
            type="button"
            onClick={remove}
            disabled={del.isPending}
          >
            <TrashSimple size={14} /> Delete
          </GhostButton>
        </Row>
      </Stack>
    </EditCard>
  );
}

export function Transactions() {
  const [filters, setFilters] = useState<TransactionFilters>(emptyFilters);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [bulkCategory, setBulkCategory] = useState("");
  const [editing, setEditing] = useState<Transaction | null>(null);

  const accounts = useAccounts();
  const categories = useCategories();
  const page = useTransactions(filters);
  const update = useUpdateTransaction();
  const bulk = useBulkCategorize();
  const saveRule = useSaveMerchantRule();
  const meta = useMeta();

  const [rulePrompt, setRulePrompt] = useState<{
    merchantRaw: string;
    categoryId: number;
  } | null>(null);

  const categorize = useCallback(
    (t: Transaction, categoryId: number | null) => {
      update.mutate({ id: t.id, category_id: categoryId });
      if (categoryId && t.merchant_raw && !meta.demo_mode) {
        setRulePrompt({ merchantRaw: t.merchant_raw, categoryId });
      }
    },
    [update, meta.demo_mode],
  );

  async function createRuleFromPrompt() {
    if (!rulePrompt) return;
    const suggestion = await suggestRule(rulePrompt.merchantRaw);
    await saveRule.mutateAsync({
      pattern: suggestion.pattern,
      match_type: suggestion.match_type,
      merchant_clean: suggestion.merchant_clean,
      category_id: rulePrompt.categoryId,
    });
    setRulePrompt(null);
  }

  const categoriesById = useMemo(() => {
    const map = new Map<number, Category>();
    (categories.data ?? []).forEach((c) => map.set(c.id, c));
    return map;
  }, [categories.data]);

  const accountName = useMemo(() => {
    const map = new Map<number, string>();
    (accounts.data ?? []).forEach((a) => map.set(a.id, a.name));
    return map;
  }, [accounts.data]);

  function setFilter<K extends keyof TransactionFilters>(
    key: K,
    value: TransactionFilters[K] | "",
  ) {
    setFilters((f) => ({
      ...f,
      page: 1,
      [key]: value === "" ? undefined : value,
    }));
    setRowSelection({});
  }

  const categoryOptions = categories.data ?? [];

  const columns = useMemo(
    () => [
      column.display({
        id: "select",
        header: ({ table }) => (
          <input
            type="checkbox"
            aria-label="Select page"
            checked={table.getIsAllRowsSelected()}
            onChange={table.getToggleAllRowsSelectedHandler()}
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            aria-label={`Select ${row.original.id}`}
            checked={row.getIsSelected()}
            onChange={row.getToggleSelectedHandler()}
          />
        ),
      }),
      column.accessor("date", {
        header: "Date",
        cell: (info) => formatDate(info.getValue()),
      }),
      column.display({
        id: "merchant",
        header: "Merchant",
        cell: ({ row }) => {
          const t = row.original;
          return (
            <>
              {t.merchant_clean || t.merchant_raw || t.description || "—"}
              {t.needs_review && (
                <ReviewBadge>
                  <Warning size={12} weight="fill" /> review
                </ReviewBadge>
              )}
            </>
          );
        },
      }),
      column.accessor("account_id", {
        header: "Account",
        cell: (info) => accountName.get(info.getValue()) ?? info.getValue(),
      }),
      column.accessor("category_id", {
        header: "Category",
        cell: ({ row }) => {
          const t = row.original;
          const category = t.category_id
            ? categoriesById.get(t.category_id)
            : undefined;
          return (
            <CategorySelect
              value={t.category_id ?? ""}
              $nature={category?.nature}
              onChange={(e) =>
                categorize(
                  t,
                  e.target.value ? Number(e.target.value) : null,
                )
              }
            >
              <option value="">Uncategorized</option>
              {categoryOptions.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </CategorySelect>
          );
        },
      }),
      column.accessor("amount", {
        header: () => <span>Amount</span>,
        cell: ({ row }) => {
          const t = row.original;
          return (
            <Amount $in={t.direction === "in"}>
              {t.direction === "in" ? "+" : "−"}
              {formatMoney(t.amount, t.currency)}
            </Amount>
          );
        },
      }),
      column.accessor("amount_usd", {
        header: "USD",
        cell: ({ row }) => (
          <Amount $in={row.original.direction === "in"}>
            {formatMoney(row.original.amount_usd, "USD")}
          </Amount>
        ),
      }),
      column.display({
        id: "edit",
        header: "",
        cell: ({ row }) => {
          const t = row.original;
          if (meta.demo_mode) return null;
          if (t.kind === "transfer") {
            return (
              <Muted as="span" title="Edit this on the Transfers screen">
                <ArrowsLeftRight size={14} /> transfer
              </Muted>
            );
          }
          return (
            <GhostButton
              type="button"
              aria-label={`Edit ${t.id}`}
              onClick={() => setEditing(t)}
            >
              <PencilSimple size={14} />
            </GhostButton>
          );
        },
      }),
    ],
    [accountName, categoriesById, categoryOptions, categorize, meta.demo_mode],
  );

  const rows = page.data?.items ?? [];

  const table = useReactTable({
    data: rows,
    columns,
    state: { rowSelection },
    getRowId: (r) => String(r.id),
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
  });

  const selectedIds = Object.keys(rowSelection).map(Number);

  async function exportCsv() {
    const query = filtersToParams({
      ...filters,
      page: undefined,
      page_size: undefined,
    });
    const res = await fetch(
      `${import.meta.env.VITE_API_BASE_URL ?? ""}/api/transactions/export?${query}`,
      { headers: { Authorization: `Bearer ${getToken() ?? ""}` } },
    );
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "transactions.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  const total = page.data?.total ?? 0;
  const pageNum = filters.page ?? 1;
  const pageSize = filters.page_size ?? 50;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  const rightAlign = new Set(["amount", "amount_usd"]);

  return (
    <Stack $gap="lg">
      <PageTitle>Transactions</PageTitle>

      {editing && (
        <EditTransactionPanel
          key={editing.id}
          txn={editing}
          categories={categoryOptions}
          onClose={() => setEditing(null)}
        />
      )}

      {rulePrompt && (
        <RulePrompt>
          <Muted as="span">
            Always categorise{" "}
            <strong>{rulePrompt.merchantRaw}</strong> as{" "}
            <strong>
              {categoriesById.get(rulePrompt.categoryId)?.name ?? "this"}
            </strong>
            ?
          </Muted>
          <Row $gap="sm">
            <Button
              type="button"
              disabled={saveRule.isPending}
              onClick={createRuleFromPrompt}
            >
              Create rule
            </Button>
            <GhostButton type="button" onClick={() => setRulePrompt(null)}>
              Not now
            </GhostButton>
          </Row>
        </RulePrompt>
      )}

      <Filters>
        <Input
          type="date"
          aria-label="From"
          value={filters.from ?? ""}
          onChange={(e) => setFilter("from", e.target.value)}
        />
        <Input
          type="date"
          aria-label="To"
          value={filters.to ?? ""}
          onChange={(e) => setFilter("to", e.target.value)}
        />
        <Select
          aria-label="Account"
          value={filters.account ?? ""}
          onChange={(e) =>
            setFilter("account", e.target.value ? Number(e.target.value) : "")
          }
        >
          <option value="">All accounts</option>
          {(accounts.data ?? []).map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Category"
          value={filters.category ?? ""}
          onChange={(e) =>
            setFilter("category", e.target.value ? Number(e.target.value) : "")
          }
        >
          <option value="">All categories</option>
          {categoryOptions.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Currency"
          value={filters.currency ?? ""}
          onChange={(e) => setFilter("currency", e.target.value)}
        >
          <option value="">Any currency</option>
          <option value="USD">USD</option>
          <option value="BRL">BRL</option>
        </Select>
        <Select
          aria-label="Nature"
          value={filters.nature ?? ""}
          onChange={(e) => setFilter("nature", e.target.value)}
        >
          <option value="">Any nature</option>
          {["essential", "discretionary", "setup", "fee", "income"].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </Select>
        <Input
          placeholder="Search merchant / notes"
          value={filters.q ?? ""}
          onChange={(e) => setFilter("q", e.target.value)}
        />
      </Filters>

      <Bar>
        <Row $gap="sm">
          {selectedIds.length > 0 && !meta.demo_mode && (
            <>
              <Muted as="span">{selectedIds.length} selected</Muted>
              <InlineSelect
                value={bulkCategory}
                onChange={(e) => setBulkCategory(e.target.value)}
              >
                <option value="">Set category…</option>
                <option value="none">Uncategorized</option>
                {categoryOptions.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </InlineSelect>
              <Button
                type="button"
                disabled={!bulkCategory || bulk.isPending}
                onClick={async () => {
                  await bulk.mutateAsync({
                    transaction_ids: selectedIds,
                    category_id:
                      bulkCategory === "none" ? null : Number(bulkCategory),
                  });
                  setRowSelection({});
                  setBulkCategory("");
                }}
              >
                Apply
              </Button>
            </>
          )}
        </Row>
        <GhostButton type="button" onClick={exportCsv}>
          <DownloadSimple size={16} />
          Export CSV
        </GhostButton>
      </Bar>

      <TableScroll>
        <Table>
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => {
                  const HeaderCell = rightAlign.has(header.column.id)
                    ? RightTh
                    : Th;
                  return (
                    <HeaderCell key={header.id}>
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                    </HeaderCell>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => {
                  const Cell = rightAlign.has(cell.column.id) ? RightTd : Td;
                  return (
                    <Cell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </Cell>
                  );
                })}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <Td colSpan={columns.length}>
                  <Muted as="span">No transactions match these filters.</Muted>
                </Td>
              </tr>
            )}
          </tbody>
        </Table>
      </TableScroll>

      <Bar>
        <Muted as="span">
          {total} transaction{total === 1 ? "" : "s"}
        </Muted>
        <Row $gap="sm">
          <GhostButton
            type="button"
            disabled={pageNum <= 1}
            onClick={() =>
              setFilters((f) => ({ ...f, page: (f.page ?? 1) - 1 }))
            }
          >
            Previous
          </GhostButton>
          <Muted as="span">
            {pageNum} / {pageCount}
          </Muted>
          <GhostButton
            type="button"
            disabled={pageNum >= pageCount}
            onClick={() =>
              setFilters((f) => ({ ...f, page: (f.page ?? 1) + 1 }))
            }
          >
            Next
          </GhostButton>
        </Row>
      </Bar>
    </Stack>
  );
}
