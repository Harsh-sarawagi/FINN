import Link from "next/link";

const features = [
  { title: "Portfolio", text: "Build and manage your tracked NSE/BSE company universe.", href: "/portfolio" },
  { title: "Market overview", text: "Refresh and review stored prices, changes, and data freshness.", href: "/dashboard" },
  { title: "Research", text: "Explore financial metrics, documents, announcements, and source-grounded questions.", href: "/research" },
];

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 sm:py-16">
      <section className="rounded-3xl bg-slate-950 px-6 py-12 text-white sm:px-10 sm:py-16">
        <p className="text-sm font-semibold uppercase tracking-widest text-emerald-300">ENAM AI Engineer Build Challenge</p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight sm:text-6xl">Investment intelligence, grounded in sources.</h1>
        <p className="mt-5 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">FINN connects portfolio tracking, market data, company intelligence, research, alerts, and an evidence-aware research assistant.</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/dashboard" className="rounded-xl bg-emerald-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-300">Open dashboard</Link>
          <Link href="/portfolio" className="rounded-xl border border-slate-600 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-900">Manage portfolio</Link>
        </div>
      </section>
      <section className="mt-6 grid gap-4 md:grid-cols-3">
        {features.map((feature) => (
          <Link key={feature.href} href={feature.href} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-md">
            <h2 className="text-lg font-semibold text-slate-950">{feature.title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">{feature.text}</p>
            <span className="mt-4 inline-block text-sm font-semibold text-emerald-700">Open module →</span>
          </Link>
        ))}
      </section>
    </main>
  );
}
