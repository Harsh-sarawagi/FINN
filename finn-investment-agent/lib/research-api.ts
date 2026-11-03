import { apiRequest } from "./api-client";

export interface ResearchCompany { id: number; ticker: string; name: string; exchange: string }
export interface FinancialComparison { metric: string; period_label: string; value: number | null; unit: string; qoq_percent: number | null; qoq_derived: boolean; yoy_percent: number | null; yoy_derived: boolean; basis: string; source_url: string; source_name: string }
export interface ResearchDocument { id: number; title: string; document_type: string; source_url: string; source_name: string; published_at: string | null; period_label: string | null }
export interface Guidance { id: number; statement: string; period_label: string | null; source_url: string; source_name: string; published_at: string | null; extracted: boolean }
export interface ResearchInsight { category: string; metric: string; severity: string; title: string; explanation: string; source_type?: string; is_prediction: boolean }
export interface TrendPoint { period_end: string; revenue: number | null; ebitda: number | null; pat: number | null; ebitda_margin: number | null; pat_margin: number | null }
export interface Research { company: ResearchCompany; provider_status: string; provider_error: string | null; is_demo: boolean; comparisons: FinancialComparison[]; periods: { period_end: string; period_label: string; basis: string; unit: string; values: Record<string, number> }[]; documents: ResearchDocument[]; guidance: Guidance[]; financial_health: Record<string, number | null>; trend: TrendPoint[]; ml_insights: ResearchInsight[]; model_scope: string }

export const searchResearchCompanies = (query: string) => apiRequest<ResearchCompany[]>(`/api/v1/research/companies?query=${encodeURIComponent(query)}`);
export const syncResearch = (ticker: string, exchange = "NSE") => apiRequest<Research>("/api/v1/research/sync", { method: "POST", body: JSON.stringify({ ticker, exchange }) });
export const getResearch = (ticker: string, exchange = "NSE") => apiRequest<Research>(`/api/v1/research/companies/${encodeURIComponent(ticker)}?exchange=${encodeURIComponent(exchange)}`);
export const compareResearchCompanies = (tickers: string[]) => apiRequest<Array<{ company: ResearchCompany; comparisons: FinancialComparison[]; financial_health: Record<string, number | null> }>>(`/api/v1/research/compare?${tickers.map((ticker) => `tickers=${encodeURIComponent(ticker)}`).join("&")}`);

export interface AssistantCitation { type: string; label: string; url: string; source_name: string; period?: string | null; reference?: string | null; basis?: string | null }
export interface AssistantAnswer { company: { ticker: string; name: string; exchange: string }; question: string; answer: string; answer_type: string; citations: AssistantCitation[]; evidence_count: number }
export const askResearchAssistant = (ticker: string, question: string, exchange = "NSE") => apiRequest<AssistantAnswer>(`/api/v1/research/assistant/${encodeURIComponent(ticker)}`, { method: "POST", body: JSON.stringify({ question, exchange }) });
