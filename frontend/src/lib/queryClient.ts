import {
  MutationCache,
  QueryCache,
  QueryClient,
} from "@tanstack/react-query";

import { pushToast } from "../components/Toast";
import { ApiError } from "./api";

function message(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 0) return "Could not reach the server.";
    return err.message;
  }
  if (err instanceof Error) return err.message || "Request failed.";
  return "Something went wrong.";
}

export const queryClient = new QueryClient({
  // Surface every failed read/write as a toast — a 401 is handled by the auth
  // layer (redirect to login), so don't double-report it.
  queryCache: new QueryCache({
    onError: (err) => {
      if (!(err instanceof ApiError) || err.status !== 401) {
        pushToast("error", message(err));
      }
    },
  }),
  mutationCache: new MutationCache({
    onSuccess: () => pushToast("success", "Saved"),
    onError: (err) => {
      if (!(err instanceof ApiError) || err.status !== 401) {
        pushToast("error", message(err));
      }
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
