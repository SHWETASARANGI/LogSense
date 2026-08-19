import { useAsync } from "./useAsync";
import { api } from "@/api/client";

interface LogFilters {
  service_name?: string;
  log_level?: string;
  limit?: number;
  offset?: number;
}

export function useLogs(filters: LogFilters = {}) {
  return useAsync(() => api.listLogs(filters), [JSON.stringify(filters)]);
}
