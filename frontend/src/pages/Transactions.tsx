import { DownloadSimple, Warning } from "@phosphor-icons/react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
  type RowSelectionState,
} from "@tanstack/react-table";
import { useCallback, useMemo, useState } from "react";
import styled from "styled-components";

import {
  Badge,
  Button,
  Card,
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
import { getToken } from "../lib/api";
import { formatDate, formatMoney } from "../lib/format";
import { useMeta } from "../lib/meta";
import {
  filtersToParams,
  suggestRule,
  useAccounts,
  useBulkCategorize,
  useCategories,
  useSaveMerchantRule,
  useTransactions,
  useUpdateTransaction,
  type TransactionFilters,
} from "../lib/queries";
import type { Theme } from "../theme";
import type { Category, Transaction } from "../lib/types";

const Filters = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: ${({ theme }) => theme.space.sm};
`;

const Bar = styled(Row)`
  justify-content: space-between;
`;

const InlineSelect = styled(Select)`
  padding: ${({ theme }) => `${theme.space.xxs} ${theme.space.xs}`};
  font-size: ${({ theme }) => theme.fontSize.xs};
  max-width: 180px;
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

export function Transactions() {
  const [filters, setFilters] = useState<TransactionFilters>(emptyFilters);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [bulkCategory, setBulkCategory] = useState("");

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
    ],
    [accountName, categoriesById, categoryOptions, categorize],
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
