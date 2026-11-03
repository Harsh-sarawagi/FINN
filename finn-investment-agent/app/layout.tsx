import type { Metadata } from "next";
import { MainNav } from "@/components/main-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "FINN",
  description: "Financial investment workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#f4f7fb] text-[#102033] antialiased">
        <header className="sticky top-0 z-40 border-b border-[#dce4ef] bg-white/95 shadow-[0_1px_12px_rgba(15,23,42,0.04)] backdrop-blur">
          <MainNav />
        </header>
        {children}
      </body>
    </html>
  );
}
