"use client";

import { useCallback, useEffect, useState } from "react";

import { addPortfolioCompany, Company, discoverCompany, getCompanies, getPortfolio, getPortfolioHistory, PortfolioHistoryItem, PortfolioMember, removePortfolioCompany } from "@/lib/portfolio-api";

type Tab = "active" | "history" | "discover";

export default function PortfolioPage() {
  const [tab, setTab] = useState<Tab>("active");
  const [members, setMembers] = useState<PortfolioMember[]>([]);
  const [history, setHistory] = useState<PortfolioHistoryItem[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [query, setQuery] = useState("");
  const [discoverTicker, setDiscoverTicker] = useState("");
  const [discoverExchange, setDiscoverExchange] = useState("NSE");
  const [loading, setLoading] = useState(true);
  const [busyTicker, setBusyTicker] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadPortfolio = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [active, historical, catalog] = await Promise.all([getPortfolio(), getPortfolioHistory(), getCompanies()]);
      setMembers(active);
      setHistory(historical);
      setCompanies(catalog);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load portfolio data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => {
      void loadPortfolio();
    }, 0);
    return () => window.clearTimeout(initialLoad);
  }, [loadPortfolio]);

  async function searchCompanies() {
    setLoading(true);
    setError("");
    try {
      setCompanies(await getCompanies(query));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Company search failed.");
    } finally {
      setLoading(false);
    }
  }

  async function addCompany(company: Company) {
    setBusyTicker(`${company.exchange}:${company.ticker}`);
    setError("");
    setNotice("");
    try {
      await addPortfolioCompany(company.ticker, company.exchange);
      setNotice(`${company.exchange}:${company.ticker} added to the active portfolio.`);
      await loadPortfolio();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The company could not be added.");
    } finally {
      setBusyTicker("");
    }
  }

  async function removeCompany(member: PortfolioMember) {
    setBusyTicker(`${member.company.exchange}:${member.company.ticker}`);
    try {
      await removePortfolioCompany(member.company.ticker, member.company.exchange);
      setNotice(`${member.company.exchange}:${member.company.ticker} removed. Historical data was preserved.`);
      await loadPortfolio();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The company could not be removed.");
    } finally {
      setBusyTicker("");
    }
  }

  async function discover() {
    if (!discoverTicker.trim()) return;
    setBusyTicker(`${discoverExchange}:${discoverTicker.trim().toUpperCase()}`);
    setError("");
    setNotice("");
    try {
      const company = await discoverCompany(discoverTicker, discoverExchange);
      setNotice(`${company.exchange}:${company.ticker} was added to the local company catalog.`);
      setDiscoverTicker("");
      await loadPortfolio();
      setCompanies(await getCompanies(company.ticker));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The company could not be discovered.");
    } finally {
      setBusyTicker("");
    }
  }

  const activeSymbols = new Set(members.map((member) => `${member.company.exchange}:${member.company.ticker}`));
  const removedByCompany = new Map(history.filter((item) => item.action === "removed").map((item) => [`${item.company.exchange}:${item.company.ticker}`, item]));

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 sm:py-10">
      <div className="mb-8">
        <p className="text-sm font-semibold uppercase tracking-widest text-emerald-700">Workspace</p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-950">Portfolio</h1>
      </div>
      <nav className="mb-6 flex flex-wrap gap-2" aria-label="Portfolio views">
        {(["active", "history", "discover"] as Tab[]).map((value) => <button key={value} type="button" onClick={() => setTab(value)} className={`rounded-full px-4 py-2 text-sm font-semibold ${tab === value ? "bg-emerald-700 text-white" : "bg-slate-100 text-slate-700"}`}>{value === "active" ? "Active Portfolio" : value === "history" ? "Portfolio History" : "Discover Companies"}</button>)}
      </nav>
      {notice && <p role="status" className="mb-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{notice}</p>}
      {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {loading ? <p className="text-sm text-slate-500">Loading portfolio…</p> : tab === "active" ? (
        members.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 px-6 py-12 text-center text-slate-500">No companies are currently active. Open Discover Companies to add one.</div> :
          <div className="grid gap-3 sm:grid-cols-2">{members.map((member) => {
            const symbol = `${member.company.exchange}:${member.company.ticker}`;
            return <article key={member.id} className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><p className="font-semibold text-slate-950">{member.company.name}</p><p className="mt-1 break-all text-sm text-slate-500">{symbol}</p></div><button type="button" disabled={busyTicker === symbol} onClick={() => void removeCompany(member)} className="min-h-10 rounded-lg px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50">Remove</button></article>;
          })}</div>
      ) : tab === "history" ? (
        history.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 px-6 py-12 text-center text-slate-500">Portfolio history will appear after companies are added or removed.</div> :
          <div className="space-y-3">{history.map((item) => {
            const symbol = `${item.company.exchange}:${item.company.ticker}`;
            const active = activeSymbols.has(symbol);
            return <article key={item.id} className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><p className="font-semibold">{item.company.name}</p><p className="mt-1 break-all text-sm text-slate-500">{symbol} · Previous status: {item.previous_status}</p><p className="mt-1 text-xs text-slate-400">{item.action === "added" ? "Added" : "Removed"}: {new Date(item.occurred_at).toLocaleString()}</p></div>{item.action === "removed" && !active && <button type="button" disabled={busyTicker === symbol} onClick={() => void addCompany(item.company)} className="min-h-10 rounded-lg border border-emerald-700 px-3 py-2 text-sm font-semibold text-emerald-700 disabled:opacity-50">Restore</button>}</article>;
          })}</div>
      ) : (
        <div className="space-y-6">
          <form onSubmit={(event) => { event.preventDefault(); void searchCompanies(); }} className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:flex-row">
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search company name or NSE/BSE symbol" className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm" />
            <button type="submit" disabled={loading} className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white">Search catalog</button>
          </form>
          <div className="grid gap-3 sm:grid-cols-2">{companies.map((company) => {
            const symbol = `${company.exchange}:${company.ticker}`;
            const removed = removedByCompany.has(symbol);
            return <article key={company.id} className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><p className="font-semibold">{company.name}</p><p className="mt-1 break-all text-sm text-slate-500">{symbol}{removed ? " · Previously removed" : ""}</p></div>{activeSymbols.has(symbol) ? <span className="text-sm font-semibold text-slate-500">Active</span> : <button type="button" disabled={busyTicker === symbol} onClick={() => void addCompany(company)} className="min-h-10 rounded-lg border border-emerald-700 px-3 py-2 text-sm font-semibold text-emerald-700 disabled:opacity-50">{removed ? "Restore" : "Add"}</button>}</article>;
          })}</div>
          {!companies.length && <p className="text-sm text-slate-500">No matching companies in the catalog.</p>}
          <section className="rounded-2xl border border-dashed border-slate-300 p-5">
            <h2 className="font-semibold">Discover an unlisted company</h2>
            <p className="mt-1 text-sm text-slate-500">FINN validates the symbol through its market provider before saving it locally.</p>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row"><select value={discoverExchange} onChange={(event) => setDiscoverExchange(event.target.value)} className="rounded-xl border border-slate-300 px-3 py-3 text-sm"><option>NSE</option><option>BSE</option></select><input value={discoverTicker} onChange={(event) => setDiscoverTicker(event.target.value.toUpperCase())} placeholder="Exchange symbol" className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm" /><button type="button" disabled={busyTicker !== ""} onClick={() => void discover()} className="rounded-xl bg-emerald-700 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50">Discover & add</button></div>
          </section>
        </div>
      )}
    </main>
  );
}
