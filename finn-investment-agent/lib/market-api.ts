import { apiRequest } from "./api-client";

export interface DashboardInstrument {
  ticker: string;
  name: string;
  exchange: string;
  price: number | null;
  change_percent: number | null;
  volume: number | null;
  price_date: string | null;
  history: { price_date: string; close: number }[];
}

export interface DashboardMover {
  ticker: string;
  name: string;
  change_percent: number;
  price: number;
}

export interface MarketDashboard {
  live_data: boolean;
  is_demo_data: boolean;
  source: string;
  last_updated: string | null;
  portfolio_count: number;
  portfolio_average_change: number | null;
  advancing_count: number;
  declining_count: number;
  instruments: DashboardInstrument[];
  top_gainers: DashboardMover[];
  top_losers: DashboardMover[];
}

export function getDashboard() {
  return apiRequest<MarketDashboard>("/api/v1/dashboard");
}

export function syncMarketData() {
  return apiRequest<unknown>("/api/v1/market/sync", { method: "POST" });
}
