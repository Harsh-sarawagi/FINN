"use client";

import { useCallback, useEffect, useState } from "react";

import { getAlerts, IntelligenceAlert, markAlertRead } from "@/lib/intelligence-api";
import { apiBaseUrl } from "@/lib/api-client";

const sevenDaysAgo = () => Date.now() - 7 * 24 * 60 * 60 * 1000;

export function NotificationDrawer() {
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState<IntelligenceAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const cutoff = sevenDaysAgo();
      const items = await getAlerts();
      setAlerts(items.filter((item) => {
        const created = new Date(item.created_at).getTime();
        return Number.isFinite(created) && created >= cutoff;
      }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Notifications could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => { void loadNotifications(); }, 0);
    return () => window.clearTimeout(timeout);
  }, [loadNotifications]);

  useEffect(() => {
    const source = new EventSource(`${apiBaseUrl}/api/v1/events/stream`);
    source.addEventListener("notifications.updated", () => { void loadNotifications(); });
    return () => source.close();
  }, [loadNotifications]);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  async function markRead(id: number) {
    setAlerts((current) => current.map((alert) => alert.id === id ? { ...alert, is_read: true } : alert));
    try {
      await markAlertRead(id);
      await loadNotifications();
    } catch {
      setAlerts((current) => current.map((alert) => alert.id === id ? { ...alert, is_read: false } : alert));
      setError("The notification could not be marked as read.");
    }
  }

  const unreadCount = alerts.filter((alert) => !alert.is_read).length;

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="relative grid h-10 w-10 place-items-center rounded-full border border-slate-200 bg-white text-slate-700 hover:bg-slate-50" aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ""}`}>
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-2">
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
          <path d="M10 21h4" />
        </svg>
        {unreadCount > 0 && <span className="absolute -right-1 -top-1 grid min-h-5 min-w-5 place-items-center rounded-full bg-emerald-600 px-1 text-[10px] font-bold text-white">{unreadCount > 99 ? "99+" : unreadCount}</span>}
      </button>
      {open && (
        <div className="fixed inset-0 z-50">
          <button type="button" aria-label="Close notifications" onClick={() => setOpen(false)} className="absolute inset-0 bg-slate-950/30 backdrop-blur-[2px]" />
          <aside className="absolute bottom-0 right-0 top-0 flex h-[100dvh] w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-2xl sm:w-[440px]" aria-label="Notifications">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div><p className="text-lg font-bold text-slate-950">Notifications</p><p className="text-xs text-slate-500">Last 7 days</p></div>
              <button type="button" onClick={() => setOpen(false)} className="grid h-10 w-10 place-items-center rounded-full text-xl text-slate-600 hover:bg-slate-100" aria-label="Close">×</button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {loading && <p className="py-8 text-center text-sm text-slate-500">Loading notifications…</p>}
              {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
              {error && <button type="button" onClick={() => void loadNotifications()} className="mt-3 rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-red-700">Retry</button>}
              {!loading && !error && alerts.length === 0 && <div className="mx-auto mt-16 max-w-xs text-center"><div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-emerald-50 text-xl text-emerald-700">✓</div><p className="mt-4 font-semibold text-slate-900">No recent notifications</p><p className="mt-1 text-sm leading-6 text-slate-500">New alerts from your configured rules will appear here.</p></div>}
              <div className="space-y-3">
                {alerts.map((alert) => (
                  <article key={alert.id} className={`rounded-2xl border p-4 ${alert.is_read ? "border-slate-100 bg-white" : "border-emerald-200 bg-emerald-50/70"}`}>
                    <div className="flex items-start gap-3">
                      <div className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${alert.is_read ? "bg-slate-300" : "bg-emerald-500"}`} />
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold leading-5 text-slate-950">{alert.title}</p>
                        {alert.message && <p className="mt-1 text-sm leading-5 text-slate-600">{alert.message}</p>}
                        <p className="mt-2 text-xs text-slate-500">{new Date(alert.created_at).toLocaleString()}</p>
                        {alert.announcement.source_url && <a href={alert.announcement.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-block text-xs font-semibold text-emerald-700">View source</a>}
                        {!alert.is_read && <button type="button" onClick={() => void markRead(alert.id)} className="ml-4 mt-3 text-xs font-semibold text-emerald-700">Mark read</button>}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
