// User and Authentication Types
export interface User {
  id: string;
  email: string;
  name: string;
  dealershipName: string;
  dealershipUrl: string;
  role: 'user' | 'admin';
}

// Competitor Types
export interface Competitor {
  id: number;
  url: string;
  name: string;
  lastScraped?: string;
}

export interface CompetitorFormData {
  url: string;
  name: string;
}

// Tool Comparison Types
export interface ToolComparison {
  payment_calculator: ToolData;
  apr_disclosure: ToolData;
  lease_payment_options: ToolData;
  pre_qualification_tool: ToolData;
  trade_in_tool: ToolData;
  online_finance_application: ToolData;
  srp_payments_shown: ToolData;
  vdp_payments_shown: ToolData;
}

export interface ToolData {
  host: boolean;
  competitors: boolean[];
  market_pct: number;
}

// Inventory Types
export interface InventoryMetrics {
  count: number;
  avg_price: number;
  vs_market: number;
}

export interface VehicleTypeData {
  host: InventoryMetrics;
  competitors: InventoryMetrics[];
  market_avg: {
    count: number;
    avg_price: number;
  };
}

export interface ConditionData {
  trucks: VehicleTypeData;
  suvs: VehicleTypeData;
  sedans: VehicleTypeData;
}

export interface InventoryData {
  new: ConditionData;
  used: ConditionData;
  cpo: ConditionData;
}

// Dossier Types
export interface DossierSummary {
  id: string;
  generatedAt: string;
  status: 'complete' | 'processing' | 'failed';
  competitorCount: number;
}

export interface Dossier {
  id: string;
  generated_at: string;
  host: {
    name: string;
    url: string;
  };
  competitors: {
    name: string;
    url: string;
  }[];
  tool_comparison: ToolComparison;
  inventory: InventoryData;
  ask_why_available: boolean;
}

// Ask Why Types
export interface AskWhyQuestion {
  id: string;
  question: string;
  section: string;
}

export interface AskWhyAnswer {
  question: string;
  answer: string;
  details: string[];
}

// Admin Types
export interface AdminScrape {
  id: number;
  userId: number;
  userName: string;
  triggeredBy: string;
  startedAt: string;
  completedAt?: string;
  status: 'pending' | 'processing' | 'complete' | 'failed';
  errorMessage?: string;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

export interface CompetitorsResponse {
  competitors: Competitor[];
  max_competitors: number;
  next_scrape: string;
}
