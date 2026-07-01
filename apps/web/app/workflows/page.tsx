"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchWithTimeout } from "../fetchWithTimeout";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

type WorkflowDefinition = {
  id: string;
  title: string;
  description: string;
  cadence: string;
  delivery: string;
  status: "Active";
};

type WorkflowAuthState = "checking" | "signed-in" | "signed-out";

const activeWorkflows: readonly WorkflowDefinition[] = [
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

export default function WorkflowsPage() {
  const router = useRouter();
  const [authState, setAuthState] = useState<WorkflowAuthState>("checking");

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
              <Link className="button button-secondary" href="/chat-with-reliability">
                Ask Polaris
              </Link>
              <Link className="button button-secondary" href="/">
                Back home
              </Link>
            </div>
          </nav>

          <div className="workflow-page-heading">
            <p className="panel-label">Workflow control</p>
            <h1>Active workflows</h1>
            <p>
              Scheduled reliability reviews currently configured for Polaris
              Watch.
            </p>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-8 md:px-8">
        <div className="workflow-card-grid">
          {activeWorkflows.map((workflow) => (
            <article className="workflow-card" key={workflow.id}>
              <div className="workflow-card-topline">
                <span className="workflow-status">{workflow.status}</span>
                <span>{workflow.cadence}</span>
              </div>
              <h2>{workflow.title}</h2>
              <p>{workflow.description}</p>
              <dl className="workflow-card-details">
                <div>
                  <dt>Delivery</dt>
                  <dd>{workflow.delivery}</dd>
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
