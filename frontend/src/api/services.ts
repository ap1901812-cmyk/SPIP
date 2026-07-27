import { fetchApi, setToken } from "./client";
import type {
  Allocation,
  ForecastCalculationResult,
  IngestionResult,
  InventorySnapshot,
  LoginResponse,
  Material,
  PlanningCalculationResult,
  Plant,
  PurchaseOrder,
  SapStatusResponse,
  UserProfile,
  Vendor,
} from "./types";

export const authApi = {
  login: async (email: string, password: string): Promise<LoginResponse> => {

    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const res = await fetchApi<LoginResponse>("/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData.toString(),
    });
    setToken(res.access_token);
    return res;
  },

  getCurrentUser: async (): Promise<UserProfile> => {
    return fetchApi<UserProfile>("/auth/me");
  },

  logout: () => {
    setToken(null);
  },
};

export const domainApi = {
  getPlants: (): Promise<Plant[]> => fetchApi<Plant[]>("/plants"),
  getMaterials: (): Promise<Material[]> => fetchApi<Material[]>("/materials"),
  getVendors: (): Promise<Vendor[]> => fetchApi<Vendor[]>("/vendors"),
  
  getInventory: (plantCode?: string): Promise<InventorySnapshot[]> => {
    const q = plantCode ? `?plant_code=${encodeURIComponent(plantCode)}` : "";
    return fetchApi<InventorySnapshot[]>(`/inventory${q}`);
  },

  getPurchaseOrders: (plantCode?: string): Promise<PurchaseOrder[]> => {
    const q = plantCode ? `?plant_code=${encodeURIComponent(plantCode)}` : "";
    return fetchApi<PurchaseOrder[]>(`/purchase-orders${q}`);
  },
};

export const planningApi = {
  getMaterialPlanning: (materialCode: string, plantCode: string): Promise<PlanningCalculationResult> => {
    return fetchApi<PlanningCalculationResult>(
      `/planning/materials/${encodeURIComponent(materialCode)}?plant_code=${encodeURIComponent(plantCode)}`
    );
  },

  getPlanningSummary: (plantCode?: string): Promise<PlanningCalculationResult[]> => {
    const q = plantCode ? `?plant_code=${encodeURIComponent(plantCode)}` : "";
    return fetchApi<PlanningCalculationResult[]>(`/planning/summary${q}`);
  },
};

export const forecastingApi = {
  getMaterialForecast: (
    materialCode: string,
    plantCode: string,
    horizonDays = 12
  ): Promise<ForecastCalculationResult> => {
    return fetchApi<ForecastCalculationResult>(
      `/forecasts/materials/${encodeURIComponent(materialCode)}?plant_code=${encodeURIComponent(plantCode)}&horizon_days=${horizonDays}`
    );
  },

  getForecastSummary: (plantCode?: string, horizonDays = 12): Promise<ForecastCalculationResult[]> => {
    const q = plantCode
      ? `?plant_code=${encodeURIComponent(plantCode)}&horizon_days=${horizonDays}`
      : `?horizon_days=${horizonDays}`;
    return fetchApi<ForecastCalculationResult[]>(`/forecasts/summary${q}`);
  },
};

export const allocationsApi = {
  createAllocation: (data: {
    plant_code: string;
    material_code: string;
    vendor_code?: string;
    allocated_quantity: number;
    uom?: string;
  }): Promise<Allocation> => {
    return fetchApi<Allocation>("/allocations", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  listAllocations: (filters?: {
    plant_code?: string;
    material_code?: string;
    status?: string;
  }): Promise<Allocation[]> => {
    const params = new URLSearchParams();
    if (filters?.plant_code) params.append("plant_code", filters.plant_code);
    if (filters?.material_code) params.append("material_code", filters.material_code);
    if (filters?.status) params.append("status", filters.status);
    const q = params.toString() ? `?${params.toString()}` : "";
    return fetchApi<Allocation[]>(`/allocations${q}`);
  },

  getAllocation: (id: number): Promise<Allocation> => {
    return fetchApi<Allocation>(`/allocations/${id}`);
  },

  updateAllocation: (
    id: number,
    data: { allocated_quantity?: number; vendor_code?: string; version: number }
  ): Promise<Allocation> => {
    return fetchApi<Allocation>(`/allocations/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  submitAllocation: (id: number): Promise<Allocation> => {
    return fetchApi<Allocation>(`/allocations/${id}/submit`, {
      method: "POST",
    });
  },

  approveAllocation: (id: number): Promise<Allocation> => {
    return fetchApi<Allocation>(`/allocations/${id}/approve`, {
      method: "POST",
    });
  },

  rejectAllocation: (id: number, rejection_reason: string): Promise<Allocation> => {
    return fetchApi<Allocation>(`/allocations/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ rejection_reason }),
    });
  },
};

export const ingestionApi = {
  uploadFile: (file: File, entityType: "consumption" | "inventory"): Promise<IngestionResult> => {
    const formData = new FormData();
    formData.append("file", file);
    const isXlsx = file.name.endsWith(".xlsx");
    const endpoint = isXlsx ? "/imports/xlsx" : "/imports/csv";
    return fetchApi<IngestionResult>(`${endpoint}?entity_type=${entityType}`, {
      method: "POST",
      body: formData,
    });
  },

  getSapStatus: (): Promise<SapStatusResponse> => fetchApi<SapStatusResponse>("/sap/status"),

  syncSapData: (): Promise<{ status: string; adapter_mode: string; synced_counts: Record<string, number> }> => {
    return fetchApi("/sap/sync", { method: "POST" });
  },
};

export const notificationsApi = {
  getNotifications: (unreadOnly = false, limit = 50, offset = 0) => {
    const q = `?unread_only=${unreadOnly}&limit=${limit}&offset=${offset}`;
    return fetchApi<{ items: import("./types").NotificationItem[]; total: number }>(`/notifications${q}`);
  },

  getUnreadCount: () => {
    return fetchApi<{ unread_count: number }>("/notifications/unread-count");
  },

  markAsRead: (id: number) => {
    return fetchApi<import("./types").NotificationItem>(`/notifications/${id}/read`, { method: "PATCH" });
  },

  markAllAsRead: () => {
    return fetchApi<{ unread_count: number }>("/notifications/mark-all-read", { method: "POST" });
  },
};

export const reportsApi = {
  getPreview: (
    reportType = "planning_summary",
    plantCode?: string,
    materialCode?: string,
    criticalityStatus?: string,
    status?: string
  ) => {
    const params = new URLSearchParams();
    params.append("report_type", reportType);
    if (plantCode) params.append("plant_code", plantCode);
    if (materialCode) params.append("material_code", materialCode);
    if (criticalityStatus) params.append("criticality_status", criticalityStatus);
    if (status) params.append("status", status);
    return fetchApi<{ title: string; headers: string[]; rows: (string | number)[][]; total_records: number }>(
      `/reports?${params.toString()}`
    );
  },

  requestExport: (payload: {
    report_type: string;
    format: "csv" | "xlsx";
    plant_code?: string;
    material_code?: string;
    criticality_status?: string;
    status?: string;
  }) => {
    return fetchApi<{
      export_id: string;
      report_type: string;
      format: string;
      status: string;
      created_at: string;
      download_url: string;
    }>("/reports/exports", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
