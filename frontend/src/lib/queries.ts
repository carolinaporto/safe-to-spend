import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api, apiForm } from "./api";
import type {
  Account,
  ByCategory,
  CardPanel,
  CashflowMonth,
  Category,
  DashboardBalances,
  DashboardOverview,
  ImportCommitResult,
  ImportPreview,
  IncomeSummary,
  MerchantRule,
  MonthBudget,
  MonthSummary,
  Person,
  PersonBalance,
  PlanConfig,
  Projection,
  RecurringRule,
  ReviewQueue,
  Transaction,
  TransactionPage,
  Transfer,
  TransferSummary,
} from "./types";

// ---------------------------------------------------------------- accounts

export function useAccounts() {
  return useQuery({
    queryKey: ["accounts"],
    queryFn: () => api<Account[]>("/api/accounts"),
  });
}

function invalidateLedger(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["accounts"] });
  qc.invalidateQueries({ queryKey: ["transactions"] });
  qc.invalidateQueries({ queryKey: ["dashboard"] });
  qc.invalidateQueries({ queryKey: ["review-queue"] });
  qc.invalidateQueries({ queryKey: ["budgets"] });
  qc.invalidateQueries({ queryKey: ["people"] });
  qc.invalidateQueries({ queryKey: ["transfers"] });
  qc.invalidateQueries({ queryKey: ["income"] });
}

export function useSaveAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id?: number } & Record<string, unknown>) => {
      const { id, ...body } = input;
      return id
        ? api<Account>(`/api/accounts/${id}`, {
            method: "PATCH",
            body: JSON.stringify(body),
          })
        : api<Account>("/api/accounts", {
            method: "POST",
            body: JSON.stringify(body),
          });
    },
    onSuccess: () => invalidateLedger(qc),
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api<void>(`/api/accounts/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidateLedger(qc),
  });
}

// -------------------------------------------------------------- categories

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: () => api<Category[]>("/api/categories"),
  });
}

export function useSaveCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id?: number } & Record<string, unknown>) => {
      const { id, ...body } = input;
      return id
        ? api<Category>(`/api/categories/${id}`, {
            method: "PATCH",
            body: JSON.stringify(body),
          })
        : api<Category>("/api/categories", {
            method: "POST",
            body: JSON.stringify(body),
          });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["categories"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
}

export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api<void>(`/api/categories/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  });
}

// ------------------------------------------------------------ transactions

export interface TransactionFilters {
  from?: string;
  to?: string;
  account?: number;
  category?: number;
  kind?: string;
  currency?: string;
  nature?: string;
  q?: string;
  needs_review?: boolean;
  page?: number;
  page_size?: number;
}

export function filtersToParams(filters: TransactionFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  }
  return params.toString();
}

export function useTransactions(filters: TransactionFilters) {
  const query = filtersToParams(filters);
  return useQuery({
    queryKey: ["transactions", query],
    queryFn: () => api<TransactionPage>(`/api/transactions?${query}`),
    placeholderData: (prev) => prev,
  });
}

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api<Transaction>("/api/transactions", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidateLedger(qc),
  });
}

export function useUpdateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number } & Record<string, unknown>) =>
      api<Transaction>(`/api/transactions/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidateLedger(qc),
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api<void>(`/api/transactions/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidateLedger(qc),
  });
}

export function useBulkCategorize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      transaction_ids: number[];
      category_id: number | null;
    }) =>
      api<{ updated: number }>("/api/transactions/bulk-categorize", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidateLedger(qc),
  });
}

// --------------------------------------------------------------- dashboard

export function useDashboardBalances() {
  return useQuery({
    queryKey: ["dashboard", "balances"],
    queryFn: () => api<DashboardBalances>("/api/dashboard/balances"),
  });
}

export function useOverview() {
  return useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: () => api<DashboardOverview>("/api/dashboard/overview"),
  });
}

export function useByCategory(params: { from?: string; to?: string } = {}) {
  const query = filtersToParams(params);
  return useQuery({
    queryKey: ["dashboard", "by-category", query],
    queryFn: () => api<ByCategory>(`/api/dashboard/by-category?${query}`),
  });
}

export function useMonthSummary(month: string) {
  return useQuery({
    queryKey: ["dashboard", "month", month],
    queryFn: () =>
      api<MonthSummary>(`/api/dashboard/month?month=${month}`),
    placeholderData: (prev) => prev,
  });
}

export function useCashflow(months = 12) {
  return useQuery({
    queryKey: ["dashboard", "cashflow", months],
    queryFn: () =>
      api<{ months: CashflowMonth[] }>(
        `/api/dashboard/cashflow?months=${months}`,
      ),
  });
}

export function useProjection() {
  return useQuery({
    queryKey: ["dashboard", "projection"],
    queryFn: () => api<Projection>("/api/dashboard/projection"),
  });
}

// ----------------------------------------------------------------- budgets

export function useBudget(month: string) {
  return useQuery({
    queryKey: ["budgets", month],
    queryFn: () => api<MonthBudget>(`/api/budgets/${month}`),
  });
}

export function useSaveBudget(month: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (
      entries: {
        category_id: number | null;
        amount_usd: string;
        rollover: boolean;
      }[],
    ) =>
      api<MonthBudget>(`/api/budgets/${month}`, {
        method: "PUT",
        body: JSON.stringify({ entries }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["budgets"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useCopyBudget(month: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api<MonthBudget>(`/api/budgets/${month}/copy-from-previous`, {
        method: "POST",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["budgets"] }),
  });
}

// ------------------------------------------------------------- plan config

export function usePlanConfig() {
  return useQuery({
    queryKey: ["plan-config"],
    queryFn: () => api<PlanConfig>("/api/plan-config"),
  });
}

export function useSavePlanConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<PlanConfig>) =>
      api<PlanConfig>("/api/plan-config", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["plan-config"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

// ----------------------------------------------------------- merchant rules

export function useMerchantRules() {
  return useQuery({
    queryKey: ["merchant-rules"],
    queryFn: () => api<MerchantRule[]>("/api/merchant-rules"),
  });
}

export function useSaveMerchantRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id?: number } & Record<string, unknown>) => {
      const { id, ...body } = input;
      return id
        ? api<MerchantRule>(`/api/merchant-rules/${id}`, {
            method: "PATCH",
            body: JSON.stringify(body),
          })
        : api<MerchantRule>("/api/merchant-rules", {
            method: "POST",
            body: JSON.stringify(body),
          });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["merchant-rules"] }),
  });
}

export function useDeleteMerchantRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api<void>(`/api/merchant-rules/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["merchant-rules"] }),
  });
}

export function suggestRule(merchantRaw: string) {
  return api<{
    pattern: string;
    match_type: string;
    merchant_clean: string | null;
  }>(`/api/merchant-rules/suggest?merchant_raw=${encodeURIComponent(merchantRaw)}`);
}

// ----------------------------------------------------------------- imports

function importForm(
  accountId: number,
  parser: string,
  file: File,
  extra: Record<string, string> = {},
): FormData {
  const form = new FormData();
  form.set("account_id", String(accountId));
  if (parser) form.set("parser", parser);
  form.set("file", file);
  for (const [k, v] of Object.entries(extra)) form.set(k, v);
  return form;
}

export function useImportPreview() {
  return useMutation({
    mutationFn: ({
      accountId,
      parser,
      file,
    }: {
      accountId: number;
      parser: string;
      file: File;
    }) =>
      apiForm<ImportPreview>(
        "/api/imports/preview",
        importForm(accountId, parser, file),
      ),
  });
}

export function useImportCommit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      accountId,
      parser,
      file,
      overrides,
      skip,
    }: {
      accountId: number;
      parser: string;
      file: File;
      overrides: Record<string, number | null>;
      skip: string[];
    }) =>
      apiForm<ImportCommitResult>(
        "/api/imports/commit",
        importForm(accountId, parser, file, {
          overrides: JSON.stringify(overrides),
          skip: JSON.stringify(skip),
        }),
      ),
    onSuccess: () => {
      invalidateLedger(qc);
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["merchant-rules"] });
    },
  });
}

export function useReviewQueue() {
  return useQuery({
    queryKey: ["review-queue"],
    queryFn: () => api<ReviewQueue>("/api/imports/review-queue"),
  });
}

// ------------------------------------------------------------------ people

export function usePeople() {
  return useQuery({
    queryKey: ["people", "list"],
    queryFn: () => api<Person[]>("/api/people"),
  });
}

export function usePeopleBalances() {
  return useQuery({
    queryKey: ["people", "balances"],
    queryFn: () => api<PersonBalance[]>("/api/people/balances"),
  });
}

export function useSavePerson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id?: number } & Record<string, unknown>) => {
      const { id, ...body } = input;
      return id
        ? api<Person>(`/api/people/${id}`, {
            method: "PATCH",
            body: JSON.stringify(body),
          })
        : api<Person>("/api/people", {
            method: "POST",
            body: JSON.stringify(body),
          });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["people"] }),
  });
}

export function useDeletePerson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api<void>(`/api/people/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["people"] }),
  });
}

export function useSettlePerson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, account_id }: { id: number; account_id: number }) =>
      api<Transaction>(`/api/people/${id}/settle`, {
        method: "POST",
        body: JSON.stringify({ account_id }),
      }),
    onSuccess: () => invalidateLedger(qc),
  });
}

// --------------------------------------------------------------- transfers

export function useTransfers() {
  return useQuery({
    queryKey: ["transfers", "list"],
    queryFn: () => api<Transfer[]>("/api/transfers"),
  });
}

export function useTransferSummary() {
  return useQuery({
    queryKey: ["transfers", "summary"],
    queryFn: () => api<TransferSummary>("/api/transfers/summary"),
  });
}

export function useCreateTransfer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api<Transfer>("/api/transfers", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidateLedger(qc),
  });
}

export function useUpdateTransfer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number } & Record<string, unknown>) =>
      api<Transfer>(`/api/transfers/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidateLedger(qc),
  });
}

export function useDeleteTransfer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api<void>(`/api/transfers/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidateLedger(qc),
  });
}

// --------------------------------------------------------- recurring rules

export function useRecurringRules() {
  return useQuery({
    queryKey: ["recurring-rules"],
    queryFn: () => api<RecurringRule[]>("/api/recurring-rules"),
  });
}

export function useSaveRecurringRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id?: number } & Record<string, unknown>) => {
      const { id, ...body } = input;
      return id
        ? api<RecurringRule>(`/api/recurring-rules/${id}`, {
            method: "PATCH",
            body: JSON.stringify(body),
          })
        : api<RecurringRule>("/api/recurring-rules", {
            method: "POST",
            body: JSON.stringify(body),
          });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recurring-rules"] }),
  });
}

export function useDeleteRecurringRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api<void>(`/api/recurring-rules/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recurring-rules"] }),
  });
}

export function useRunRecurringRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api<{ generated: number }>(`/api/recurring-rules/${id}/run`, {
        method: "POST",
      }),
    onSuccess: () => {
      invalidateLedger(qc);
      qc.invalidateQueries({ queryKey: ["recurring-rules"] });
    },
  });
}

// ------------------------------------------------------------------ income

export function useIncomeSummary() {
  return useQuery({
    queryKey: ["income", "summary"],
    queryFn: () => api<IncomeSummary>("/api/income/summary"),
  });
}

// ------------------------------------------------------------------- cards

export function useCards() {
  return useQuery({
    queryKey: ["dashboard", "cards"],
    queryFn: () => api<CardPanel[]>("/api/dashboard/cards"),
  });
}
