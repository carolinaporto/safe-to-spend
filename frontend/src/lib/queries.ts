import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "./api";
import type {
  Account,
  ByCategory,
  CashflowMonth,
  Category,
  DashboardBalances,
  DashboardOverview,
  MonthBudget,
  PlanConfig,
  Projection,
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
