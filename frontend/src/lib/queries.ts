import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "./api";
import type {
  Account,
  Category,
  DashboardBalances,
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
