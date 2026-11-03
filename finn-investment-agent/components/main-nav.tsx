"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NotificationDrawer } from "./notification-drawer";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/research", label: "Research" },
];

export function MainNav() {
  const pathname = usePathname();

  return (
    <nav className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6" aria-label="Main navigation">
      <Link href="/" className="text-xl font-bold tracking-tight text-emerald-800">FINN</Link>
      <div className="hidden items-center gap-1 md:flex">
        {links.map((link) => {
          const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
          return (
            <Link key={link.href} href={link.href} aria-current={active ? "page" : undefined}
              className={`rounded-lg px-3 py-2 text-sm font-semibold whitespace-nowrap ${active ? "bg-emerald-50 text-emerald-800" : "text-slate-700 hover:bg-slate-100"}`}>
              {link.label}
            </Link>
          );
        })}
      </div>
      <div className="flex items-center gap-2">
        <NotificationDrawer />
      </div>
      <div className="order-3 flex w-full justify-center gap-1 border-t border-slate-100 pt-2 md:hidden">
          {links.map((link) => (
            <Link key={link.href} href={link.href} aria-label={link.label} className={`rounded-lg px-2.5 py-2 text-xs font-semibold ${pathname === link.href ? "bg-emerald-50 text-emerald-800" : "text-slate-700"}`}>{link.label}</Link>
          ))}
      </div>
    </nav>
  );
}
