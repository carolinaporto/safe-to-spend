import { useQuery } from "@tanstack/react-query";

import { api } from "./api";

export interface Meta {
  demo_mode: boolean;
  import_enabled: boolean;
}

const FALLBACK: Meta = { demo_mode: false, import_enabled: true };

/**
 * Public instance configuration. Drives demo-mode UI: hiding the import
 * screen and disabling destructive actions. Safe to call before login.
 */
export function useMeta(): Meta {
  const { data } = useQuery({
    queryKey: ["meta"],
    queryFn: () => api<Meta>("/api/meta"),
    staleTime: Infinity,
  });
  return data ?? FALLBACK;
}
