export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: string[];
}


export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface Plant {
  id: number;
  code: string;
  name: string;
  location?: string;
}

export interface Material {
  id: number;
  code: string;
  description: string;
  material_type: string;
  base_uom: string;
}

export interface Vendor {
  id: number;
  code: string;
  name: string;
  contact_email?: string;
  is_active: boolean;
}

export interface InventorySnapshot {
  id: number;
  plant_code: string;
  material_code: string;
  snapshot_date: string;
  usable_physical_stock: number;
  reserved_stock: number;
  blocked_stock: number;
  uom: string;
}

export interface PurchaseOrderLine {
  id: number;
  line_number: number;
  material_code: string;
  order_quantity: number;
  open_quantity: number;
  uom: string;
  expected_delivery_date: string;
  status: string;
}

export interface PurchaseOrder {
  id: number;
  po_number: string;
  vendor_code: string;
  plant_code: string;
  status: string;
  po_date: string;
  lines: PurchaseOrderLine[];
}

export interface PlanningCalculationResult {
  plant_code: string;
  plant_name: string;
  material_code: string;
  material_description: string;
  base_uom: string;
  as_of_timestamp: string;
  average_daily_demand: number;
  demand_std_dev: number;
  observation_days_count: number;
  lead_time_days: number;
  lead_time_source: string;
  service_level_z: number;
  abc_class: string;
  safety_stock: number;
  is_safety_stock_overridden: boolean;
  usable_physical_stock: number;
  reserved_stock_info: number;
  blocked_stock_info: number;
  eligible_incoming_po_qty: number;
  committed_allocations: number;
  planning_availability: number;
  demand_during_lead_time: number;
  reorder_point: number;
  criticality_status: "CRITICAL" | "WARNING" | "HEALTHY";
  explanation: string;
}

export interface ForecastDayPoint {
  day_offset: number;
  forecast_date: string;
  forecasted_quantity: number;
  uom: string;
}

export interface ForecastCalculationResult {
  plant_code: string;
  material_code: string;
  base_uom: string;
  generated_at: string;
  forecast_horizon_days: number;
  historical_window_days: number;
  selected_model: string;
  evaluation_metric_name: string;
  evaluation_metric_value: number;
  is_fallback: boolean;
  fallback_reason?: string;
  total_forecasted_demand: number;
  average_forecasted_daily_demand: number;
  point_forecasts: ForecastDayPoint[];
}

export interface Allocation {
  id: number;
  allocation_number: string;
  plant_code: string;
  plant_name: string;
  material_code: string;
  material_description: string;
  vendor_code?: string;
  vendor_name?: string;
  allocated_quantity: number;
  uom: string;
  status: "DRAFT" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED";
  created_by_email: string;
  approved_by_email?: string;
  rejection_reason?: string;
  sap_reference_id?: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface IngestionResult {
  success: boolean;
  entity_type: string;
  imported_records: number;
  total_rows: number;
  errors: Array<{ row: number; field: string; message: string }>;
}

export interface SapStatusResponse {
  adapter_mode: string;
  is_mock: boolean;
  message: string;
}

export interface NotificationItem {
  id: number;
  user_id: number;
  notification_type: string;
  title: string;
  message: string;
  resource_type?: string;
  resource_id?: string;
  is_read: boolean;
  read_at?: string;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  total: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}
