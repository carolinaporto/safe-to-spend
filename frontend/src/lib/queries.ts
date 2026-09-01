import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api, apiForm } from "./api";
import type {
  Account,
  ByCategory,
  CashflowMonth,
  Category,
  DashboardBalances,
  DashboardOverview,
  ImportCommitResult,
  ImportPreview,
  MerchantRule,
  MonthBudget,
  PlanConfig,
  Projection,
  ReviewQueue,
  Transaction,
  TransactionPage,
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
