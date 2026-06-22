import { apiClient } from "./apiClient";

const BASE = "/api/v1/nse-reports";

export interface BhavCopyRecord {
  id: string;
  file_date: string;        // "YYYY-MM-DD"
  file_name: string;
  file_size_bytes: number | null;
  downloaded_at: string | null;
  status: "pending" | "downloaded" | "failed";
  error_message: string | null;
}

export interface BhavCopyListResponse {
  records: BhavCopyRecord[];
  total: number;
}

export const nseReportsApi = {
  /** Last N calendar days (default 7) */
  list: async (days = 7): Promise<BhavCopyListResponse> => {
    const { data } = await apiClient.get<BhavCopyListResponse>(BASE + "/", {
      params: { days },
    });
    return data;
  },

  /** Full paginated history */
  listAll: async (limit = 50, offset = 0): Promise<BhavCopyListResponse> => {
    const { data } = await apiClient.get<BhavCopyListResponse>(BASE + "/all", {
      params: { limit, offset },
    });
    return data;
  },

  /** Returns a URL to stream-download the ZIP */
  downloadUrl: (fileDate: string): string =>
    `${BASE}/download/${fileDate}`,

  /** Staff only — manually kick off a download */
  triggerDownload: async (fileDate?: string): Promise<{ message: string; date: string }> => {
    const { data } = await apiClient.post(`${BASE}/trigger`, null, {
      params: fileDate ? { file_date: fileDate } : undefined,
    });
    return data;
  },
};
