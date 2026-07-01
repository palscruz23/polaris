"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchWithTimeout } from "../fetchWithTimeout";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

type PolarisWatchReviewDefinition = {
  id: string;
  title: string;
  description: string;
  cadence: string;
  delivery: string;
  status: "Active";
};

type PolarisWatchAuthState = "checking" | "signed-in" | "signed-out";

const activePolarisWatchReviews: readonly PolarisWatchReviewDefinition[] = [
  {
    id: "breakdown-strategy-gap",
    title: "Breakdown Strategy Gap Review",
    description:
      "Reviews recent breakdown-like work orders against maintenance strategy coverage to surface gaps that need engineering attention.",
    cadence: "Daily scheduled review",
    delivery: "Microsoft Teams report",
    status: "Active",
  },
  {
    id: "bad-actor-watchlist",
    title: "Bad Actor Watchlist",
    description:
      "Ranks chronic equipment and repeat failure patterns so reliability teams can focus the next investigation on the highest-impact assets.",
    cadence: "Daily scheduled review",
    delivery: "Microsoft Teams report",
    status: "Active",
  },
  {
    id: "maintenance-strategy-health-check",
    title: "Maintenance Strategy Health Check",
    description:
      "Checks maintenance strategy profiles, observed failure-mode coverage, frequency risks, and recommended strategy changes.",
    cadence: "Daily scheduled review",
    delivery: "Microsoft Teams report",
    status: "Active",
  },
];

export default function PolarisWatchPage() {
  const router = useRouter();
  const [authState, setAuthState] =
    useState<PolarisWatchAuthState>("checking");

  useEffect(() => {
    const requestController = new AbortController();

    async function checkSession() {
      if (!API_URL) {
        setAuthState("signed-out");
        router.replace("/login?next=/workflows");
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
      router.replace("/login?next=/workflows");
    }

    checkSession();

    return () => requestController.abort();
  }, [router]);

  if (authState === "checking") {
    return (
      <main className="workflow-page min-h-screen bg-[var(--background)] text-[var(--foreground)]">
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
    <main className="workflow-page min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <header className="workflow-page-header border-b border-[var(--border)]">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-8 md:px-8">
          <nav className="app-nav flex items-center justify-between gap-6">
            <Link href="/" className="brand-link text-lg font-semibold">
              <span>Open Reliability</span>
            </Link>
            <div className="workflow-header-actions">
              <Link className="button button-secondary" href="/ask-polaris">
                Ask Polaris
              </Link>
              <Link className="button button-secondary" href="/">
                Back home
              </Link>
            </div>
          </nav>

          <div className="workflow-page-heading">
            <p className="panel-label">Scheduled review watch</p>
            <h1>Polaris Watch</h1>
            <p>
              Active scheduled reliability reviews monitored by Polaris Watch.
            </p>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-8 md:px-8">
        <div className="workflow-card-grid">
          {activePolarisWatchReviews.map((review) => (
            <article className="workflow-card" key={review.id}>
              <div className="workflow-card-topline">
                <span className="workflow-status">{review.status}</span>
                <span>{review.cadence}</span>
              </div>
              <h2>{review.title}</h2>
              <p>{review.description}</p>
              <dl className="workflow-card-details">
                <div>
                  <dt>Delivery</dt>
                  <dd>{review.delivery}</dd>
                </div>
                <div>
                  <dt>Last run</dt>
                  <dd>Run history pending</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
