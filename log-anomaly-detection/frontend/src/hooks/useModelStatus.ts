import { useAsync } from "./useAsync";
import { api } from "@/api/client";

export function useModelStatus() {
  return useAsync(() => api.getModelStatus(), []);
}
