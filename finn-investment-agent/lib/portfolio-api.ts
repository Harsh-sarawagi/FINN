import { apiRequest } from "./api-client";

export interface Company {
  id: number;
  ticker: string;
  name: string;
  exchange: string;
}

export interface PortfolioMember {
  id: number;
  company_id: number;
  added_at: string;
  company: Company;
  is_active: boolean;
  removed_at: string | null;
  previous_status: string;
}

export interface PortfolioHistoryItem {
  id: number;
  company_id: number;
  action: string;
  previous_status: string;
  occurred_at: string;
  company: Company;
}

export function getPortfolio() {
  return apiRequest<PortfolioMember[]>("/api/v1/portfolio");
}

export const getPortfolioHistory = () => apiRequest<PortfolioHistoryItem[]>("/api/v1/portfolio/history");
export const getCompanies = (query = "") => apiRequest<Company[]>(`/api/v1/companies${query ? `?q=${encodeURIComponent(query)}` : ""}`);
export const discoverCompany = (ticker: string, exchange = "NSE", name?: string) => apiRequest<Company>("/api/v1/companies/discover", {
  method: "POST",
  body: JSON.stringify({ ticker, exchange, name }),
});

export function addPortfolioCompany(ticker: string, exchange = "NSE") {
  return apiRequest<PortfolioMember>("/api/v1/portfolio", {
    method: "POST",
    body: JSON.stringify({ ticker, exchange }),
  });
}

export function removePortfolioCompany(ticker: string, exchange = "NSE") {
  return apiRequest<void>(
    `/api/v1/portfolio/${encodeURIComponent(ticker)}?exchange=${encodeURIComponent(exchange)}`,
    { method: "DELETE" },
  );
}
