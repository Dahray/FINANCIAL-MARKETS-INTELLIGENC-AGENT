/**
 * Institutional API Client & Authenticated Fetch Wrapper for FMIP Next.js Dashboard.
 */

import type {
  AssistantAskResponse,
  CompetitorEvent,
  CompetitorProfile,
  OpportunityRadarItem,
  RegulatoryEvent,
  SourceRegisterEntry,
  WeeklyReportSummary,
} from "@/types/intelligence";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

const TOKEN_STORAGE_KEY = "fmip_access_token";
const USER_STORAGE_KEY = "fmip_current_user";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function setAuthSession(token: string, user: AuthUser): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

export function clearAuthSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(USER_STORAGE_KEY);
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error (${response.status}): ${errorText}`);
  }
  return (await response.json()) as T;
}

export const fmipApi = {
  login: async (email: string, password: string) => {
    const res = await apiFetch<{
      access_token: string;
      refresh_token: string;
      user: AuthUser;
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setAuthSession(res.access_token, res.user);
    return res;
  },

  getOverviewDashboard: () => apiFetch<any>("/overview/dashboard"),

  getMarketTimeseries: (symbol: string, limit = 60) =>
    apiFetch<any[]>(
      `/markets/timeseries?symbol=${encodeURIComponent(symbol)}&limit=${limit}`
    ),

  getSymbolAnalytics: (symbol: string) =>
    apiFetch<any>(`/markets/analytics/${encodeURIComponent(symbol)}`),

  getYieldCurve: (curveName = "NGN_SOVEREIGN_FMDQ") =>
    apiFetch<any>(`/markets/yield-curve?curve_name=${encodeURIComponent(curveName)}`),

  triggerIngestion: () =>
    apiFetch<any>("/markets/ingest", { method: "POST" }),

  getMacroIndicators: (country?: string) =>
    apiFetch<any[]>(
      `/macro/indicators${country ? `?country=${encodeURIComponent(country)}` : ""}`
    ),

  getForecast: (targetCode: string, horizonSteps = 4) =>
    apiFetch<any>(
      `/macro/forecasts/${encodeURIComponent(targetCode)}?horizon_steps=${horizonSteps}`
    ),

  getEconometrics: () => apiFetch<any>("/macro/econometrics"),

  getScenarios: (portfolioValueNgn = 10_000_000_000) =>
    apiFetch<any>(`/macro/scenarios?portfolio_value_ngn=${portfolioValueNgn}`),

  getOpportunities: (opportunityClass?: string) =>
    apiFetch<OpportunityRadarItem[]>(
      `/opportunities${
        opportunityClass ? `?opportunity_class=${encodeURIComponent(opportunityClass)}` : ""
      }`
    ),

  getCompetitorProfiles: (category?: string) =>
    apiFetch<CompetitorProfile[]>(
      `/competitors/profiles${
        category ? `?category=${encodeURIComponent(category)}` : ""
      }`
    ),

  getCompetitorEvents: () => apiFetch<CompetitorEvent[]>("/competitors/events"),

  getRegulatoryEvents: (regulatorCode?: string) =>
    apiFetch<RegulatoryEvent[]>(
      `/regulatory/events${
        regulatorCode ? `?regulator_code=${encodeURIComponent(regulatorCode)}` : ""
      }`
    ),

  getSourceRegister: () =>
    apiFetch<SourceRegisterEntry[]>("/regulatory/source-register"),

  listWeeklyReports: () => apiFetch<WeeklyReportSummary[]>("/reports"),

  getWeeklyReportDetail: (reportCode = "latest") =>
    apiFetch<WeeklyReportSummary>(`/reports/${encodeURIComponent(reportCode)}`),

  generateWeeklyReport: () =>
    apiFetch<any>("/reports/generate", { method: "POST" }),

  searchArchive: (q = "", documentType = "") => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (documentType) params.set("document_type", documentType);
    const qs = params.toString();
    return apiFetch<any[]>(`/reports/archive/search${qs ? `?${qs}` : ""}`);
  },

  askAssistant: (question: string) =>
    apiFetch<AssistantAskResponse>("/assistant/ask", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
};
