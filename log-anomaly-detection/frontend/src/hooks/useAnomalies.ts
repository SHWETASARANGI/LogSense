import { useAsync } from "./useAsync";
import { api } from "@/api/client";
import type { AnomalyFilters } from "@/api/types";

export function useAnomalies(filters: AnomalyFilters = {}) {
  return useAsync(() => api.listAnomalies(filters), [JSON.stringify(filters)]);
}
