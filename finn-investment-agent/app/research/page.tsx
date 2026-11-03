"use client";

import { useEffect, useMemo, useState } from "react";
import {
  askResearchAssistant,
  AssistantAnswer,
  compareResearchCompanies,
  getResearch,
  Research,
  ResearchCompany,
  searchResearchCompanies,
  syncResearch,
} from "@/lib/research-api";

const metricNames: Record<string, string> = {
  revenue: "Revenue",
  ebitda: "EBITDA",
  pbt: "PBT",
  pat: "PAT",
};

const formatValue = (value: number | null | undefined, unit = "") => {
  if (value === null || value === undefined) return "Unavailable";
  return `${value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}${unit}`;
};

const formatChange = (value: number | null) => {
  if (value === null) return "Unavailable";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
};

function EmptyState({ children }: { children: React.ReactNode }) {
  return <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 px-5 py-10 text-center text-sm text-slate-500">{children}</div>;
}

function TrendChart({ points }: { points: Research["trend"] }) {
  const usable = points.filter((point) => point.revenue !== null || point.ebitda !== null || point.pat !== null);
  if (!usable.length) return <EmptyState>No financial trend data is available from the provider.</EmptyState>;

  const series: Array<{ key: "revenue" | "ebitda" | "pat"; label: string; color: string }> = [
    { key: "revenue", label: "Revenue", color: "#047857" },
    { key: "ebitda", label: "EBITDA", color: "#2563eb" },
    { key: "pat", label: "PAT", color: "#d97706" },
  ];
  const values = usable.flatMap((point) => series.map((item) => point[item.key]).filter((value): value is number => value !== null));
  const maximum = Math.max(...values.map((value) => Math.abs(value)), 1);
  const minimum = Math.min(...values, 0);

  const position = (value: number, index: number) => {
    const x = usable.length === 1 ? 50 : 42 + (index / (usable.length - 1)) * 716;
    const y = 210 - ((value - minimum) / (maximum - minimum || 1)) * 180;
    return { x, y };
  };

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-4 text-xs font-semibold text-slate-600">
        {series.map((item) => <span key={item.key} className="flex items-center gap-2"><i className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />{item.label}</span>)}
      </div>
      <div className="overflow-x-auto">
        <svg viewBox="0 0 800 250" className="min-w-[640px] w-full" role="img" aria-label="Revenue, EBITDA and PAT trend">
          {[30, 90, 150, 210].map((y) => <line key={y} x1="40" x2="760" y1={y} y2={y} stroke="#e2e8f0" />)}
          {series.map((item) => {
            const coordinates = usable.map((point, index) => ({ point, ...position(point[item.key] ?? 0, index) })).filter((entry) => entry.point[item.key] !== null);
            if (!coordinates.length) return null;
            const d = coordinates.map((entry, index) => `${index === 0 ? "M" : "L"} ${entry.x} ${entry.y}`).join(" ");
            return <g key={item.key}><path d={d} fill="none" stroke={item.color} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />{coordinates.map((entry) => <circle key={`${item.key}-${entry.point.period_end}`} cx={entry.x} cy={entry.y} r="4" fill="white" stroke={item.color} strokeWidth="2"><title>{`${item.label}: ${entry.point[item.key]?.toLocaleString("en-IN")} · ${entry.point.period_end}`}</title></circle>)}</g>;
          })}
          {usable.map((point, index) => {
            const x = usable.length === 1 ? 50 : 42 + (index / (usable.length - 1)) * 716;
            return <text key={point.period_end} x={x} y="238" textAnchor="middle" fontSize="11" fill="#64748b">{point.period_end}</text>;
          })}
        </svg>
      </div>
      <p className="mt-2 text-xs leading-5 text-slate-500">Provider-reported values. Units and reporting basis are retained in the detailed snapshot.</p>
    </div>
  );
}

export default function ResearchPage() {
  const [query, setQuery] = useState("");
  const [companies, setCompanies] = useState<ResearchCompany[]>([]);
  const [catalogCompanies, setCatalogCompanies] = useState<ResearchCompany[]>([]);
  const [searchFocused, setSearchFocused] = useState(false);
  const [comparisonTicker, setComparisonTicker] = useState("");
  const [research, setResearch] = useState<Research | null>(null);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [assistantQuestion, setAssistantQuestion] = useState("");
  const [assistantAnswer, setAssistantAnswer] = useState<AssistantAnswer | null>(null);
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [comparisons, setComparisons] = useState<Array<{ company: ResearchCompany; comparisons: { metric: string; value: number | null }[]; financial_health: Record<string, number | null> }>>([]);

  useEffect(() => {
    searchResearchCompanies("")
      .then(setCatalogCompanies)
      .catch(() => setCatalogCompanies([]));
  }, []);

  useEffect(() => {
    if (!query.trim()) {
      return;
    }
    const timeout = window.setTimeout(() => {
      searchResearchCompanies(query).then(setCompanies).catch(() => setCompanies([]));
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [query]);

  const selectedMetric = useMemo(() => {
    if (!research) return [];
    return research.comparisons;
  }, [research]);

  async function loadCompany(company: ResearchCompany) {
    setLoading(true);
    setError("");
    setSearched(true);
    setAssistantAnswer(null);
    setAssistantQuestion("");
    setQuery(`${company.exchange}:${company.ticker}`);
    try {
      setResearch(await getResearch(company.ticker, company.exchange));
    } catch {
      try {
        setResearch(await syncResearch(company.ticker, company.exchange));
      } catch {
        setResearch(null);
        setError("Financial and document data is unavailable for this company.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const raw = query.trim().toUpperCase();
    const exact = companies.find((company) => raw === `${company.exchange}:${company.ticker}` || raw === company.ticker || raw === company.name.toUpperCase());
    if (exact) {
      await loadCompany(exact);
      return;
    }

    const [exchangePart, tickerPart] = raw.includes(":") ? raw.split(":") : ["NSE", raw];
    const exchange = exchangePart === "BSE" ? "BSE" : "NSE";
    const ticker = (tickerPart || exchangePart).replace(/[^A-Z0-9&.-]/g, "");
    if (!ticker) return;
    setLoading(true);
    setSearched(true);
    setError("");
    setAssistantAnswer(null);
    try {
      setResearch(await syncResearch(ticker, exchange));
    } catch {
      setResearch(null);
      setError("Company resolution or provider data was unavailable. No values have been fabricated.");
    } finally {
      setLoading(false);
    }
  }

  async function askAssistant(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!research || !assistantQuestion.trim()) return;
    setAssistantLoading(true);
    setError("");
    try {
      setAssistantAnswer(await askResearchAssistant(research.company.ticker, assistantQuestion.trim(), research.company.exchange));
    } catch {
      setError("The research assistant is unavailable. No answer has been fabricated.");
    } finally {
      setAssistantLoading(false);
    }
  }

  async function compareCompany(company: ResearchCompany) {
    if (!research || company.ticker === research.company.ticker) return;
    setError("");
    try {
      setComparisons(await compareResearchCompanies([research.company.ticker, company.ticker]));
    } catch {
      setError("Company comparison data is unavailable.");
    }
  }

  function selectSuggestion(company: ResearchCompany) {
    setQuery(`${company.exchange}:${company.ticker}`);
    setSearchFocused(false);
    void loadCompany(company);
  }

  const latestPeriod = research?.periods[0];
  const availableTrends = research?.trend.filter((point) => point.revenue !== null || point.ebitda !== null || point.pat !== null) ?? [];

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-10">
      <div className="flex flex-col gap-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.24em] text-emerald-700">Pull Research</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">Equity research</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Company financials, primary sources, calculated signals, and evidence-grounded AI in one workspace.</p>
        </div>

        <form onSubmit={submit} className="relative flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm sm:flex-row">
          <label className="sr-only" htmlFor="research-search">Company name or ticker</label>
          <div className="relative min-w-0 flex-1">
            <input id="research-search" value={query} onFocus={() => setSearchFocused(true)} onChange={(event) => { setQuery(event.target.value); setSearchFocused(true); if (!event.target.value.trim()) setCompanies([]); }} placeholder="Search by company name or ticker, e.g. TCS or NSE:TCS" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-base text-slate-950 placeholder:text-slate-400" autoComplete="off" />
            {searchFocused && (
              <div className="absolute left-0 right-0 top-[calc(100%+8px)] z-30 max-h-72 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-2 shadow-xl">
                {(query.trim() ? companies : catalogCompanies).slice(0, 12).map((company) => (
                  <button type="button" key={`${company.exchange}:${company.ticker}`} onMouseDown={(event) => event.preventDefault()} onClick={() => selectSuggestion(company)} className="flex w-full items-center justify-between gap-4 rounded-xl px-3 py-3 text-left hover:bg-slate-50">
                    <span><strong className="block text-sm text-slate-950">{company.name}</strong><span className="mt-1 block text-xs text-slate-500">{company.exchange}:{company.ticker}</span></span>
                    <span className="text-xs font-bold text-emerald-700">Open</span>
                  </button>
                ))}
                {(query.trim() ? companies : catalogCompanies).length === 0 && <p className="px-3 py-4 text-sm text-slate-500">No catalog match yet. Enter an exact NSE/BSE ticker to resolve it.</p>}
              </div>
            )}
          </div>
          <button type="submit" disabled={loading || !query.trim()} className="min-h-12 rounded-xl bg-emerald-700 px-6 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">{loading ? "Loading…" : "Open research"}</button>
        </form>

        {query.trim() && searched && !loading && companies.length === 0 && !research && <p className="text-sm text-slate-500">No company in the local catalog matches this search. Use an exact NSE or BSE ticker with the Research button to attempt provider resolution.</p>}
        {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        {!research && loading && <div className="rounded-2xl border border-slate-200 bg-white px-5 py-12 text-center"><p className="font-semibold text-slate-800">Loading company research</p><p className="mt-2 text-sm text-slate-500">Checking stored data and the configured market provider…</p></div>}
        {!research && !loading && !searched && <EmptyState>Choose a company to begin. FINN will display only values returned by its providers and stored primary sources.</EmptyState>}

        {research && (
          <div className="space-y-6">
            <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
              <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
                <div><div className="flex flex-wrap items-center gap-2"><h2 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">{research.company.name}</h2><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">{research.company.exchange}:{research.company.ticker}</span></div><p className="mt-2 text-sm text-slate-500">{latestPeriod ? `Latest stored period: ${latestPeriod.period_label}` : "No stored reporting period"}</p></div>
                <div className={`rounded-xl px-4 py-3 text-sm ${research.provider_status === "available" ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}><strong>{research.is_demo ? "Demo data" : research.provider_status === "available" ? "Provider data current" : "Provider data unavailable"}</strong>{research.provider_error && <span className="block text-xs">{research.provider_error}</span>}</div>
              </div>
              <div className="mt-7 grid grid-cols-2 gap-px overflow-hidden rounded-2xl bg-slate-200 lg:grid-cols-4">
                {selectedMetric.map((item) => <div key={item.metric} className="bg-slate-50 p-4 sm:p-5"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">{metricNames[item.metric] ?? item.metric}</p><p className="mt-2 text-xl font-semibold text-slate-950">{formatValue(item.value)}</p><p className="mt-1 text-xs text-slate-500">YoY {formatChange(item.yoy_percent)}</p></div>)}
                {selectedMetric.length === 0 && <div className="col-span-full bg-slate-50 p-5 text-sm text-slate-500">No reported financial figures are stored for this company.</div>}
              </div>
            </section>

            <nav className="sticky top-[112px] z-20 overflow-x-auto rounded-2xl border border-slate-200 bg-white/95 p-2 shadow-sm backdrop-blur md:top-[72px]" aria-label="Research sections">
              {["Performance", "Quality", "Guidance", "Narrative", "Sources", "Assistant"].map((item) => <a key={item} href={`#research-${item.toLowerCase()}`} className="inline-block whitespace-nowrap rounded-lg px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 hover:text-slate-950">{item}</a>)}
            </nav>

            <section id="research-performance" className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
              <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><div className="flex items-center justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Historical performance</p><h2 className="mt-1 text-xl font-semibold text-slate-950">Revenue and profitability</h2></div><span className="text-xs text-slate-500">{availableTrends.length} periods</span></div><div className="mt-5"><TrendChart points={research.trend} /></div></article>
              <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Calculated quality</p><h2 className="mt-1 text-xl font-semibold text-slate-950">Margin trends</h2>{availableTrends.length === 0 ? <div className="mt-5"><EmptyState>No comparable margin periods are available.</EmptyState></div> : <div className="mt-5 space-y-4">{availableTrends.slice(-6).map((point) => <div key={point.period_end} className="rounded-xl bg-slate-50 p-4"><p className="text-xs font-semibold text-slate-500">{point.period_end}</p><div className="mt-2 grid grid-cols-2 gap-3"><div><span className="text-xs text-slate-500">EBITDA margin</span><strong className="block text-lg">{formatValue(point.ebitda_margin, "%")}</strong></div><div><span className="text-xs text-slate-500">PAT margin</span><strong className="block text-lg">{formatValue(point.pat_margin, "%")}</strong></div></div></div>)}</div>}</article>
            </section>

            <section id="research-quality" className="grid gap-5 lg:grid-cols-[1fr_1fr]">
              <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Balance sheet & cash flow</p><h2 className="mt-1 text-xl font-semibold">Financial quality indicators</h2><div className="mt-5 grid grid-cols-2 gap-3">{[["Debt / equity", research.financial_health.debt_to_equity, "x"], ["Current ratio", research.financial_health.current_ratio, "x"], ["Operating cash flow", research.financial_health.operating_cash_flow, ""], ["PAT margin", research.financial_health.pat_margin_percent, "%"]].map(([label, value, unit]) => <div key={String(label)} className="rounded-2xl bg-slate-50 p-4"><p className="text-xs text-slate-500">{label}</p><p className="mt-2 text-lg font-semibold text-slate-950">{formatValue(value as number | null, String(unit))}</p></div>)}</div><p className="mt-4 text-xs leading-5 text-slate-500">Calculated from stored provider values where all required inputs exist. No assumption is made for missing data.</p></article>
              <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Pattern screen</p><h2 className="mt-1 text-xl font-semibold">ML findings</h2><p className="mt-2 text-xs leading-5 text-slate-500">{research.model_scope}</p>{research.ml_insights.length === 0 ? <div className="mt-5"><EmptyState>No configured anomaly threshold was crossed.</EmptyState></div> : <div className="mt-5 space-y-3">{research.ml_insights.map((insight, index) => <div key={`${insight.metric}-${index}`} className="rounded-2xl border border-amber-200 bg-amber-50 p-4"><p className="text-xs font-bold uppercase text-amber-700">{insight.category.replaceAll("_", " ")}</p><h3 className="mt-1 font-semibold text-slate-950">{insight.title}</h3><p className="mt-2 text-sm leading-6 text-slate-700">{insight.explanation}</p><p className="mt-2 text-xs text-slate-500">Signal only; not a prediction or recommendation.</p></div>)}</div>}</article>
            </section>

            <section id="research-guidance" className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Guidance vs Actuals</p><h2 className="mt-1 text-xl font-semibold text-slate-950">Management commitments and reported outcomes</h2></div><span className="text-xs text-slate-500">Evidence, not estimates</span></div>
              {research.guidance.length === 0 ? <div className="mt-5"><EmptyState>No verified management guidance is stored. Actual results can still be reviewed below; no guidance-versus-actual comparison has been inferred.</EmptyState></div> : <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-slate-50 text-slate-500"><tr><th className="px-4 py-3">Period</th><th className="px-4 py-3">Management statement</th><th className="px-4 py-3">Latest actual</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Source</th></tr></thead><tbody>{research.guidance.map((item) => { const currentActual = selectedMetric.find((metric) => item.statement.toLowerCase().includes(metric.metric)); return <tr key={item.id} className="border-t border-slate-100"><td className="px-4 py-4 align-top text-slate-500">{item.period_label ?? "Period unavailable"}</td><td className="px-4 py-4 align-top font-medium text-slate-900">{item.statement}</td><td className="px-4 py-4 align-top">{currentActual ? `${formatValue(currentActual.value)} · ${currentActual.period_label}` : "Actual not directly matched"}</td><td className="px-4 py-4 align-top"><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">Not automatically scored</span></td><td className="px-4 py-4 align-top"><a href={item.source_url} target="_blank" rel="noreferrer" className="font-semibold text-emerald-700">{item.source_name}</a></td></tr>; })}</tbody></table></div>}
            </section>

            <section id="research-narrative" className="grid gap-5 lg:grid-cols-[1fr_1fr]">
              <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Narrative vs Numbers</p><h2 className="mt-1 text-xl font-semibold">Management narrative and reported evidence</h2><div className="mt-5 space-y-3">{research.guidance.length === 0 && research.documents.length === 0 ? <EmptyState>No management narrative or indexed primary documents are stored.</EmptyState> : <><div className="rounded-2xl bg-slate-50 p-4"><p className="text-xs font-bold text-slate-500">NARRATIVE</p><p className="mt-2 text-sm leading-6 text-slate-700">{research.guidance.length ? `${research.guidance.length} verified management guidance statement(s) are available. Statements remain separate from reported outcomes.` : "No verified management narrative is available."}</p></div><div className="rounded-2xl bg-emerald-50 p-4"><p className="text-xs font-bold text-emerald-800">NUMBERS</p><p className="mt-2 text-sm leading-6 text-slate-700">{selectedMetric.length ? `${selectedMetric.length} latest reported metric(s) are available. Calculated margins and ratios are identified separately.` : "No latest reported metrics are available."}</p></div></>}</div></article>
              <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Company comparison</p><h2 className="mt-1 text-xl font-semibold">Peer snapshot</h2>{comparisons.length === 0 ? <div className="mt-5"><EmptyState>Select a company shown in catalog search, then choose Compare to build a peer view.</EmptyState></div> : <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="text-slate-500"><tr><th className="py-2">Company</th><th>Revenue</th><th>PAT</th><th>EBITDA margin</th><th>PAT margin</th></tr></thead><tbody>{comparisons.map((item) => { const values = Object.fromEntries(item.comparisons.map((metric) => [metric.metric, metric.value])); return <tr key={`${item.company.exchange}:${item.company.ticker}`} className="border-t"><td className="py-3 font-semibold">{item.company.ticker}</td><td>{formatValue(values.revenue)}</td><td>{formatValue(values.pat)}</td><td>{formatValue(item.financial_health.ebitda_margin_percent, "%")}</td><td>{formatValue(item.financial_health.pat_margin_percent, "%")}</td></tr>; })}</tbody></table></div>}</article>
            </section>

            <section id="research-sources" className="grid gap-5 lg:grid-cols-[1fr_1fr]">
              <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Primary sources</p><h2 className="mt-1 text-xl font-semibold">Document library</h2>{research.documents.length === 0 ? <div className="mt-5"><EmptyState>No annual reports, presentations, results, or transcripts are linked to this company.</EmptyState></div> : <div className="mt-5 space-y-3">{research.documents.map((doc) => <a key={doc.id} href={doc.source_url} target="_blank" rel="noreferrer" className="block rounded-2xl border border-slate-200 p-4 hover:border-emerald-300 hover:bg-emerald-50/30"><span className="text-xs font-bold uppercase text-slate-500">{doc.document_type.replaceAll("_", " ")}</span><p className="mt-1 font-semibold text-slate-950">{doc.title}</p><p className="mt-1 text-xs text-slate-500">{doc.source_name}{doc.period_label ? ` · ${doc.period_label}` : ""} · Open source</p></a>)}</div>}</article>
              <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Reported snapshot</p><h2 className="mt-1 text-xl font-semibold">Source detail</h2>{selectedMetric.length === 0 ? <div className="mt-5"><EmptyState>No reported source rows are available.</EmptyState></div> : <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[560px] text-left text-sm"><thead className="bg-slate-50 text-slate-500"><tr><th className="px-3 py-3">Metric</th><th className="px-3 py-3">Period</th><th className="px-3 py-3">Reported</th><th className="px-3 py-3">Source</th></tr></thead><tbody>{selectedMetric.map((item) => <tr key={item.metric} className="border-t border-slate-100"><td className="px-3 py-3 font-semibold">{metricNames[item.metric] ?? item.metric}</td><td className="px-3 py-3 text-slate-500">{item.period_label}</td><td className="px-3 py-3">{formatValue(item.value)} <span className="text-xs text-slate-500">{item.unit}</span></td><td className="px-3 py-3"><a href={item.source_url} target="_blank" rel="noreferrer" className="font-semibold text-emerald-700">{item.source_name}</a></td></tr>)}</tbody></table></div>}</article>
            </section>

            <section id="research-assistant" className="rounded-3xl border border-slate-200 bg-slate-950 p-5 text-white shadow-sm sm:p-6">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-300">Evidence-grounded AI</p><h2 className="mt-2 text-xl font-semibold">Research assistant</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">Answers use stored financial data, announcements, guidance, and document excerpts. Missing evidence is reported rather than inferred. Groq credentials are required for AI interpretation; fallback remains source-grounded.</p>
              <form onSubmit={askAssistant} className="mt-5 flex flex-col gap-3 sm:flex-row"><input value={assistantQuestion} onChange={(event) => setAssistantQuestion(event.target.value)} placeholder={`Ask about ${research.company.name}`} className="min-w-0 flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white placeholder:text-slate-400" /><button disabled={assistantLoading || !assistantQuestion.trim()} className="min-h-12 rounded-xl bg-emerald-500 px-5 py-3 font-bold text-slate-950 disabled:opacity-50">{assistantLoading ? "Researching…" : "Ask FINN"}</button></form>
              {assistantLoading && <p className="mt-4 text-sm text-slate-400">Retrieving and ranking company evidence…</p>}
              {assistantAnswer && <div className="mt-5 rounded-2xl border border-slate-700 bg-slate-900 p-5"><div className="flex flex-wrap gap-2 text-xs"><span className="font-bold uppercase text-emerald-300">{assistantAnswer.answer_type === "ai_generated" ? "AI-generated interpretation" : "Source-grounded fallback"}</span><span className="text-slate-400">{assistantAnswer.evidence_count} evidence item(s)</span></div><p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-100">{assistantAnswer.answer}</p>{assistantAnswer.citations.length > 0 && <div className="mt-5 border-t border-slate-700 pt-4"><p className="text-xs font-bold uppercase text-slate-400">Sources</p><ul className="mt-3 space-y-2">{assistantAnswer.citations.map((citation, index) => <li key={`${citation.url}-${index}`}><a href={citation.url} target="_blank" rel="noreferrer" className="text-sm font-semibold text-emerald-300">{citation.label}</a><span className="ml-2 text-xs text-slate-400">{citation.source_name}{citation.period ? ` · ${citation.period}` : ""}</span></li>)}</ul></div>}</div>}
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <label htmlFor="research-comparison" className="text-sm font-semibold text-slate-700">Compare with</label>
                <select id="research-comparison" value={comparisonTicker} onChange={(event) => setComparisonTicker(event.target.value)} className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm text-slate-950">
                  <option value="">Choose catalog company</option>
                  {catalogCompanies.filter((company) => company.ticker !== research.company.ticker).map((company) => <option key={`${company.exchange}:${company.ticker}`} value={company.ticker}>{company.exchange}:{company.ticker} · {company.name}</option>)}
                </select>
                <button type="button" disabled={!comparisonTicker || loading} onClick={() => { const peer = catalogCompanies.find((company) => company.ticker === comparisonTicker); if (peer) void compareCompany(peer); }} className="min-h-11 rounded-xl bg-slate-900 px-5 py-3 text-sm font-bold text-white disabled:opacity-50">Add comparison</button>
              </div>
              {comparisons.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{comparisons.map((item) => <span key={`${item.company.exchange}:${item.company.ticker}`} className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800">{item.company.exchange}:{item.company.ticker}</span>)}</div>}
            </section>
          </div>
        )}
      </div>
    </main>
  );
}
