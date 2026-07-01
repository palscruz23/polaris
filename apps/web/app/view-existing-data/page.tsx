"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import DataTableBrowser from "./DataTableBrowser";
import { fetchWithTimeout } from "../fetchWithTimeout";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

type DataPageAuthState = "checking" | "signed-in" | "signed-out";

export default function ViewExistingDataPage() {
  const router = useRouter();
  const [authState, setAuthState] = useState<DataPageAuthState>("checking");

  useEffect(() => {
    const requestController = new AbortController();

    async function checkSession() {
      if (!API_URL) {
        setAuthState("signed-out");
        router.replace("/login?next=/view-existing-data");
        return;
      }

      try {
        const response = await fetchWithTimeout(`${API_URL}/auth/me`, {
          credentials: "include",
          signal: requestController.signal,
        });
        if (response.ok) {
          setAuthState("signed-in");
          return;
        }
      } catch {
        if (requestController.signal.aborted) {
          return;
        }
      }

      setAuthState("signed-out");
      router.replace("/login?next=/view-existing-data");
    }

    checkSession();

    return () => requestController.abort();
  }, [router]);

  if (authState === "checking") {
    return (
      <main className="data-page min-h-screen bg-[var(--background)] text-[var(--foreground)]">
        <section className="workflow-loading" aria-live="polite">
          Checking your session...
        </section>
      </main>
    );
  }

  if (authState !== "signed-in") {
    return null;
  }

  return (
    <main className="data-page min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <header className="data-page-header border-b border-[var(--border)]">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-8 md:px-8">
          <nav className="app-nav flex items-center justify-between gap-6">
            <Link href="/" className="brand-link text-lg font-semibold">
              <span>Open Reliability</span>
            </Link>
            <Link className="button button-secondary" href="/">
              Back home
            </Link>
          </nav>

          <div className="data-page-heading">
            <h1>Synthetic data</h1>
            <p>
              Browse the seeded synthetic reliability tables that back the demo.
            </p>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-8 md:px-8">
        <DataTableBrowser />
      </section>
    </main>
  );
}
