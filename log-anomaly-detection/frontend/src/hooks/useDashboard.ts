import { useAsync } from "./useAsync";
import { api } from "@/api/client";

export function useDashboard(lookbackHours = 24) {
  return useAsync(() => api.getDashboard(lookbackHours), [lookbackHours]);
}
