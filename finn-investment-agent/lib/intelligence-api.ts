import { apiRequest } from "./api-client";

export interface IntelligenceCompany { id: number; ticker: string; name: string; exchange: string }
export interface Announcement { id: number; company: IntelligenceCompany; title: string; content: string | null; category: string; source_url: string; source_name: string; published_at: string; ingested_at: string; ingestion_status: string; summary: string | null; ai_generated: boolean; is_demo: boolean }
export interface AlertRule { id: number; name: string; category: string | null; company_id: number | null; enabled: boolean }
export interface IntelligenceAlert { id: number; title: string; message: string | null; is_read: boolean; created_at: string; announcement: Announcement }
export interface DailyDigest { generated_at: string; period_hours: number; announcement_count: number; by_category: Record<string, number>; announcements: Announcement[] }
export interface IngestionStatus { status: string; source: string; records_added: number; last_attempt_at: string | null; last_success_at: string | null; error_message: string | null }

export const getAnnouncements = (category = "") => apiRequest<Announcement[]>(`/api/v1/announcements${category ? `?category=${encodeURIComponent(category)}` : ""}`);
export const ingestAnnouncements = () => apiRequest<IngestionStatus>("/api/v1/announcements/ingest", { method: "POST" });
export const getAlerts = () => apiRequest<IntelligenceAlert[]>("/api/v1/alerts");
export const markAlertRead = (id: number) => apiRequest<IntelligenceAlert>(`/api/v1/alerts/${id}/read`, { method: "PATCH" });
export const getAlertRules = () => apiRequest<AlertRule[]>("/api/v1/alert-rules");
export const createAlertRule = (name: string, category = "") => apiRequest<AlertRule>("/api/v1/alert-rules", { method: "POST", body: JSON.stringify({ name, category: category || null }) });
export const getDailyDigest = () => apiRequest<DailyDigest>("/api/v1/digest/daily");
export const getAnnouncementStatus = () => apiRequest<IngestionStatus>("/api/v1/announcements/status");
