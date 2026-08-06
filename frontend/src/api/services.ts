import { fetchApi, fetchBlob, setToken } from "./client";
import type {
  Allocation,
  ChangePasswordPayload,
  DecisionSupportSummaryDTO,
  ExecutionHistoryItem,
  ExplainabilityReportDTO,
  ForecastCalculationResult,
  FormulaEntry,
  IngestionResult,
  InventorySnapshot,
  LoginResponse,
  Material,
  PlanningCalculationResult,
  Plant,
  PurchaseOrder,
  SapStatusResponse,
  SimulationRunItem,
  TelemetryMetrics,
  UserCreatePayload,
  UserProfile,
  UserResetPasswordPayload,
  UserStatusPayload,
  UserUpdatePayload,
  Vendor,
} from "./types";

export { fetchApi } from "./client";

export const authApi = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const res = await fetchApi<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    setToken(res.access_token);
    return res;
  },

  changePassword: async (payload: ChangePasswordPayload): Promise<{ message: string }> => {
    return fetchApi<{ message: string }>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getCurrentUser: async (): Promise<UserProfile> => {
    return fetchApi<UserProfile>("/auth/me");
  },

  logout: () => {
    setToken(null);
  },
};

export const usersApi = {
  getUsers: (): Promise<UserProfile[]> => fetchApi<UserProfile[]>("/users"),
  getUser: (id: number): Promise<UserProfile> => fetchApi<UserProfile>(`/users/${id}`),
  createUser: (payload: UserCreatePayload): Promise<UserProfile & { temporary_password?: string }> =>
    fetchApi<UserProfile & { temporary_password?: string }>("/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateUser: (id: number, payload: UserUpdatePayload): Promise<UserProfile> =>
    fetchApi<UserProfile>(`/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  resetPassword: (id: number, payload: UserResetPasswordPayload): Promise<{ message: string; temporary_password?: string }> =>
    fetchApi<{ message: string; temporary_password?: string }>(`/users/${id}/reset-password`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateStatus: (id: number, payload: UserStatusPayload): Promise<UserProfile> =>
    fetchApi<UserProfile>(`/users/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
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

  uploadWorkbook: (file: File, replaceExisting = false): Promise<import("./types").WorkbookImportReport> => {
    const formData = new FormData();
    formData.append("file", file);
    return fetchApi<import("./types").WorkbookImportReport>(`/imports/workbook?replace_existing=${replaceExisting}`, {
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

  downloadFile: (downloadUrl: string) => {
    return fetchBlob(downloadUrl);
  },
};

export const finishedGoodsApi = {
  getFinishedGoods: (plantId?: number): Promise<import("./types").FinishedGoodSummary[]> => {
    const q = plantId ? `?plant_id=${plantId}` : "";
    return fetchApi<import("./types").FinishedGoodSummary[]>(`/finished-goods${q}`);
  },

  getFinishedGood: (id: number): Promise<import("./types").FinishedGoodDetail> => {
    return fetchApi<import("./types").FinishedGoodDetail>(`/finished-goods/${id}`);
  },

  getBOMExpansion: (id: number): Promise<import("./types").FGBOMExpansion> => {
    return fetchApi<import("./types").FGBOMExpansion>(`/finished-goods/${id}/bom`);
  },
};

export const bomApi = {
  getBOMs: (fgMaterialId?: number, componentMaterialId?: number, isActive?: boolean): Promise<import("./types").BOMItem[]> => {
    const params = new URLSearchParams();
    if (fgMaterialId !== undefined) params.append("fg_material_id", String(fgMaterialId));
    if (componentMaterialId !== undefined) params.append("component_material_id", String(componentMaterialId));
    if (isActive !== undefined) params.append("is_active", String(isActive));
    const q = params.toString() ? `?${params.toString()}` : "";
    return fetchApi<import("./types").BOMItem[]>(`/boms${q}`);
  },

  getBOM: (id: number): Promise<import("./types").BOMItem> => {
    return fetchApi<import("./types").BOMItem>(`/boms/${id}`);
  },

  getExpansion: (fgId: number): Promise<import("./types").FGBOMExpansion> => {
    return fetchApi<import("./types").FGBOMExpansion>(`/boms/expansion/${fgId}`);
  },
};

export const dependencyApi = {
  getWhereUsed: (materialId: number): Promise<import("./types").WhereUsedResponse> => {
    return fetchApi<import("./types").WhereUsedResponse>(`/materials/${materialId}/where-used`);
  },

  getDependencies: (materialId: number): Promise<import("./types").MaterialDependencyResponse> => {
    return fetchApi<import("./types").MaterialDependencyResponse>(`/materials/${materialId}/dependencies`);
  },
};

export const fgPlanningApi = {
  runPlanning: (request: import("./types").FGPlanningRequest): Promise<import("./types").FGPlanningResult> => {
    return fetchApi<import("./types").FGPlanningResult>("/planning/run", {
      method: "POST",
      body: JSON.stringify(request),
    });
  },

  getShortages: (plantCode?: string): Promise<import("./types").ShortageSummary> => {
    const q = plantCode ? `?plant_code=${encodeURIComponent(plantCode)}` : "";
    return fetchApi<import("./types").ShortageSummary>(`/planning/shortages${q}`);
  },

  getRecommendations: (plantCode?: string): Promise<import("./types").RecommendationSummary> => {
    const q = plantCode ? `?plant_code=${encodeURIComponent(plantCode)}` : "";
    return fetchApi<import("./types").RecommendationSummary>(`/planning/recommendations${q}`);
  },
};

export const decisionSupportApi = {
  getSummary: (plantCode: string, materialCode?: string): Promise<DecisionSupportSummaryDTO> => {
    const params = new URLSearchParams();
    params.append("plant_code", plantCode);
    if (materialCode) params.append("material_code", materialCode);
    return fetchApi<DecisionSupportSummaryDTO>(`/decision-support/summary?${params.toString()}`);
  },

  getExplainability: (plantCode: string, materialCode: string): Promise<ExplainabilityReportDTO> => {
    return fetchApi<ExplainabilityReportDTO>(
      `/decision-support/explainability?plant_code=${encodeURIComponent(plantCode)}&material_code=${encodeURIComponent(materialCode)}`
    );
  },
};

export const monitoringApi = {
  getTelemetry: (plantCode?: string): Promise<TelemetryMetrics> => {
    const q = plantCode ? `?plant_code=${encodeURIComponent(plantCode)}` : "";
    return fetchApi<TelemetryMetrics>(`/planning/executions/telemetry${q}`);
  },

  getExecutions: (plantCode?: string, limit = 50): Promise<ExecutionHistoryItem[]> => {
    const params = new URLSearchParams();
    params.append("limit", String(limit));
    if (plantCode) params.append("plant_code", plantCode);
    return fetchApi<ExecutionHistoryItem[]>(`/planning/executions?${params.toString()}`);
  },
};

export const simulationApi = {
  getSimulations: (): Promise<SimulationRunItem[]> => {
    return fetchApi<SimulationRunItem[]>("/simulations");
  },

  runSimulation: (payload: Record<string, unknown>): Promise<SimulationRunItem> => {
    return fetchApi<SimulationRunItem>("/simulations/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getSimulation: (id: number): Promise<SimulationRunItem> => {
    return fetchApi<SimulationRunItem>(`/simulations/${id}`);
  },
};

export const formulaExplorerApi = {
  getFormulas: (): Promise<FormulaEntry[]> => {
    return fetchApi<FormulaEntry[]>("/admin/formulas");
  },
};
