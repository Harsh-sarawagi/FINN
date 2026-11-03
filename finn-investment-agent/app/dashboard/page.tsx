"use client";

import { useCallback, useEffect, useState } from "react";

import { getDashboard, MarketDashboard, syncMarketData } from "@/lib/market-api";
import { Announcement, getAnnouncements, getDailyDigest, ingestAnnouncements, DailyDigest } from "@/lib/intelligence-api";
import { apiBaseUrl } from "@/lib/api-client";

function formatPercent(value: number | null) {
  return value === null ? "—" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function PriceSparkline({ points }: { points: { price_date: string; close: number }[] }) {
  if (points.length < 2) return <div className="grid h-16 place-items-center text-xs text-slate-400">Not enough history</div>;
  const width = 240;
  const height = 64;
  const values = points.map((point) => point.close);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const range = maximum - minimum || 1;
  const coordinates = values.map((value, index) => {
    const x = (index / (values.length - 1)) * width;
    const y = height - ((value - minimum) / range) * (height - 8) - 4;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const positive = values[values.length - 1] >= values[0];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-16 w-full" role="img" aria-label={`Price trend from ${points[0].price_date} to ${points[points.length - 1].price_date}`}>
      <polyline points={coordinates.join(" ")} fill="none" stroke={positive ? "#047857" : "#dc2626"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<MarketDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [digest, setDigest] = useState<DailyDigest | null>(null);
  const [category, setCategory] = useState("");
  const [intelligenceView, setIntelligenceView] = useState<"feed" | "digest">("feed");
  const [syncingAnnouncements, setSyncingAnnouncements] = useState(false);
  const [streamStatus, setStreamStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");
    let marketLoaded = false;
    try {
      setDashboard(await getDashboard());
      marketLoaded = true;
    } catch (cause) {
      setDashboard(null);
      setError(cause instanceof Error ? cause.message : "Unable to load market data.");
    } finally {
      setLoading(false);
    }

    const intelligenceRequests = await Promise.allSettled([
      getAnnouncements(category), getDailyDigest(),
    ]);
    const [feed, dailyDigest] = intelligenceRequests;
    if (feed.status === "fulfilled") {
      const cutoff = Date.now() - 45 * 24 * 60 * 60 * 1000;
      setAnnouncements(feed.value.filter((item) => {
        const published = new Date(item.published_at).getTime();
        return !Number.isFinite(published) || published >= cutoff;
      }));
    }
    else setAnnouncements([]);
    if (dailyDigest.status === "fulfilled") setDigest(dailyDigest.value);
    else setDigest(null);
    if (intelligenceRequests.some((result) => result.status === "rejected") && !marketLoaded) {
      setError("Market and intelligence services were unavailable. Confirm that the backend is running.");
    } else if (intelligenceRequests.some((result) => result.status === "rejected")) {
      setError("Market data loaded, but one or more intelligence services were unavailable.");
    }
  }, [category]);

  useEffect(() => {
    const timeout = window.setTimeout(() => { void loadDashboard(); }, 0);
    return () => window.clearTimeout(timeout);
  }, [loadDashboard]);

  useEffect(() => {
    const source = new EventSource(`${apiBaseUrl}/api/v1/events/stream`);
    source.onopen = () => setStreamStatus("connected");
    source.onerror = () => setStreamStatus("disconnected");
    source.addEventListener("connected", () => setStreamStatus("connected"));
    source.addEventListener("market.updated", () => void loadDashboard());
    source.addEventListener("announcements.updated", () => void loadDashboard());
    source.addEventListener("intelligence.updated", () => void loadDashboard());
    source.addEventListener("notifications.updated", () => void loadDashboard());
    return () => source.close();
  }, [loadDashboard]);

  async function refreshAnnouncements() {
    setSyncingAnnouncements(true);
    try {
      await ingestAnnouncements();
      await loadDashboard();
    } catch {
      setError("Announcement ingestion is unavailable. Previously stored announcements remain visible.");
    } finally {
      setSyncingAnnouncements(false);
    }
  }

  async function refreshMarketData() {
    setSyncing(true);
    setError("");
    try {
      await syncMarketData();
      await loadDashboard();
    } catch {
      setError("Market synchronization failed. The latest stored or fallback data may still be shown.");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 sm:py-10">
      <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold uppercase tracking-widest text-emerald-700">Overview</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">Market dashboard</h1>
        </div>
        <button type="button" onClick={() => void refreshMarketData()} disabled={syncing} className="min-h-12 rounded-xl bg-emerald-700 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60">
          {syncing ? "Refreshing…" : "Refresh market data"}
        </button>
      </div>

      {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      <div className="mb-4 flex items-center gap-2 text-xs font-semibold text-slate-600" role="status">
        <span className={`h-2 w-2 rounded-full ${streamStatus === "connected" ? "bg-emerald-500" : streamStatus === "connecting" ? "bg-amber-500" : "bg-red-500"}`} />
        Live updates: {streamStatus}
      </div>
      {loading ? <p className="text-sm text-slate-500">Loading dashboard…</p> : dashboard && (
        <>
          <div className={`mb-6 rounded-xl px-4 py-3 text-sm ${dashboard.live_data ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}>
            <strong>{dashboard.live_data ? "Live market data" : "Demo/fallback data"}</strong>
            {" · Source: "}{dashboard.source}{dashboard.last_updated ? ` · Last updated: ${new Date(dashboard.last_updated).toLocaleString()}` : " · No successful sync recorded"}
          </div>
          <section className="mb-6 grid gap-4 sm:grid-cols-3">
            <article className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Portfolio companies</p><p className="mt-2 text-3xl font-semibold">{dashboard.portfolio_count}</p></article>
            <article className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Average daily change</p><p className={`mt-2 text-3xl font-semibold ${dashboard.portfolio_average_change !== null && dashboard.portfolio_average_change < 0 ? "text-red-700" : "text-emerald-700"}`}>{formatPercent(dashboard.portfolio_average_change)}</p></article>
            <article className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">Advancing / declining</p><p className="mt-2 text-3xl font-semibold">{dashboard.advancing_count} / {dashboard.declining_count}</p></article>
          </section>
          <section className="grid gap-6 lg:grid-cols-2">
            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h2 className="mb-4 text-lg font-semibold">Top gainers</h2>
              {dashboard.top_gainers.length === 0 ? <p className="text-sm text-slate-500">No gainers available.</p> : dashboard.top_gainers.map((item) => <div key={item.ticker} className="flex justify-between gap-3 border-t border-slate-100 py-3"><span className="min-w-0"><strong>{item.ticker}</strong><span className="ml-2 truncate text-sm text-slate-500">{item.name}</span></span><span className="shrink-0 font-semibold text-emerald-700">{formatPercent(item.change_percent)}</span></div>)}
            </article>
            <article className="rounded-2xl border border-slate-200 bg-white p-5">
              <h2 className="mb-4 text-lg font-semibold">Top losers</h2>
              {dashboard.top_losers.length === 0 ? <p className="text-sm text-slate-500">No losers available.</p> : dashboard.top_losers.map((item) => <div key={item.ticker} className="flex justify-between gap-3 border-t border-slate-100 py-3"><span className="min-w-0"><strong>{item.ticker}</strong><span className="ml-2 truncate text-sm text-slate-500">{item.name}</span></span><span className="shrink-0 font-semibold text-red-700">{formatPercent(item.change_percent)}</span></div>)}
            </article>
          </section>
          <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <h2 className="p-5 text-lg font-semibold">Portfolio instruments</h2>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="bg-slate-50 text-slate-500"><tr><th className="px-5 py-3">Company</th><th className="px-5 py-3">Last close</th><th className="px-5 py-3">Change</th><th className="px-5 py-3">20-day trend</th><th className="px-5 py-3">Volume</th></tr></thead>
                <tbody>{dashboard.instruments.map((item) => <tr key={`${item.exchange}-${item.ticker}`} className="border-t border-slate-100">
                  <td className="px-5 py-4"><strong>{item.ticker}</strong><span className="ml-2 text-slate-500">{item.name}</span></td>
                  <td className="px-5 py-4">{item.price === null ? "Unavailable" : item.price.toLocaleString("en-IN", { style: "currency", currency: "INR" })}</td>
                  <td className="px-5 py-4">{formatPercent(item.change_percent)}</td>
                  <td className="w-64 px-5 py-2"><PriceSparkline points={item.history ?? []} /></td>
                  <td className="px-5 py-4">{item.volume?.toLocaleString("en-IN") ?? "—"}</td>
                </tr>)}</tbody>
              </table>
            </div>
          </section>

          <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <div className="flex flex-col gap-4 border-b border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Company intelligence</p>
                <h2 className="mt-1 text-lg font-semibold text-slate-950">Market activity and research</h2>
              </div>
              <div className="inline-flex w-full rounded-xl bg-slate-100 p-1 sm:w-auto" role="tablist" aria-label="Dashboard intelligence view">
                <button type="button" role="tab" aria-selected={intelligenceView === "feed"} onClick={() => setIntelligenceView("feed")} className={`flex-1 rounded-lg px-4 py-2 text-sm font-semibold sm:flex-none ${intelligenceView === "feed" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600"}`}>Intelligence feed</button>
                <button type="button" role="tab" aria-selected={intelligenceView === "digest"} onClick={() => setIntelligenceView("digest")} className={`flex-1 rounded-lg px-4 py-2 text-sm font-semibold sm:flex-none ${intelligenceView === "digest" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600"}`}>Daily digest{digest ? ` (${digest.announcement_count})` : ""}</button>
              </div>
            </div>

            {intelligenceView === "feed" ? (
              <div className="p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-slate-500">Recent company announcements and material updates.</p>
                  <button type="button" onClick={() => void refreshAnnouncements()} disabled={syncingAnnouncements} className="rounded-lg border border-emerald-700 px-3 py-2 text-sm font-semibold text-emerald-700 disabled:opacity-60">
                    {syncingAnnouncements ? "Ingesting…" : "Ingest announcements"}
                  </button>
                </div>
                <div className="mt-4 flex gap-2 overflow-x-auto pb-2">
                  {["", "financial_results", "corporate_actions", "major_orders", "management_updates", "other_material"].map((value) => <button key={value || "all"} onClick={() => setCategory(value)} className={`whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-semibold ${category === value ? "bg-emerald-700 text-white" : "bg-slate-100 text-slate-700"}`}>{value ? value.replaceAll("_", " ") : "All"}</button>)}
                </div>
                {announcements.length === 0 ? <p className="mt-6 rounded-xl bg-slate-50 px-4 py-6 text-sm text-slate-500">No announcements are currently stored. Ingest from NSE/BSE when the source is available.</p> : (
                  <div className="mt-2 divide-y divide-slate-100">
                    {announcements.map((item) => (
                      <article key={item.id} className="grid gap-4 py-5 md:grid-cols-[120px_minmax(0,1fr)_auto] md:items-start">
                        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-500 md:block">
                          <span className="rounded-md bg-slate-100 px-2 py-1 text-slate-800">{item.company.ticker}</span>
                          <span className="block mt-2">{new Date(item.published_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</span>
                        </div>
                        <div className="min-w-0">
                          <div className="flex flex-wrap gap-2 text-xs text-slate-500"><span>{item.category.replaceAll("_", " ")}</span>{item.is_demo && <span className="font-semibold text-amber-700">DEMO</span>}{item.ai_generated && <span className="font-semibold text-violet-700">AI SUMMARY</span>}</div>
                          <h3 className="mt-1 font-semibold leading-6 text-slate-950">{item.title}</h3>
                          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{item.summary || "No summary available."}</p>
                        </div>
                        {item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer" className="inline-flex min-h-10 items-center justify-center rounded-lg border border-slate-200 px-3 text-sm font-semibold text-emerald-700 hover:bg-emerald-50">View source</a>}
                      </article>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="p-5">
                {digest ? (
                  <>
                    <div className="rounded-xl bg-emerald-50 px-5 py-4">
                      <p className="text-sm font-medium text-emerald-900">{digest.announcement_count} announcements in the last 24 hours.</p>
                      <p className="mt-1 text-xs text-emerald-700">Generated {new Date(digest.generated_at).toLocaleString()}</p>
                    </div>
                    <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {Object.entries(digest.by_category).map(([key, count]) => <div key={key} className="rounded-xl border border-slate-200 p-4"><p className="text-sm text-slate-500">{key.replaceAll("_", " ")}</p><p className="mt-1 text-2xl font-semibold text-slate-950">{count}</p></div>)}
                    </div>
                    {digest.announcements.length > 0 && <div className="mt-5 divide-y divide-slate-100">{digest.announcements.map((item) => <article key={item.id} className="py-4"><p className="text-xs font-semibold text-slate-500">{item.company.ticker}</p><h3 className="mt-1 font-semibold text-slate-950">{item.title}</h3></article>)}</div>}
                  </>
                ) : <p className="rounded-xl bg-slate-50 px-4 py-6 text-sm text-slate-500">Daily digest unavailable.</p>}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
