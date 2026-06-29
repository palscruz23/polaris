"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchWithTimeout } from "../fetchWithTimeout";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

type AdminState = "checking" | "signed-out" | "authorized" | "forbidden" | "error";
type AdminTab = "users" | "evaluations";

type AuthUser = {
  email: string;
  display_name: string | null;
};

type EvalRunSummary = {
  id: string;
  suite_name: string;
  provider: string;
  model: string;
  status: string;
  case_count: number;
  passed_count: number;
  failed_count: number;
  aggregate_score: number | null;
  git_commit: string | null;
  dataset_version: string | null;
  run_metadata: Record<string, unknown> | null;
  error_type: string | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
};

type EvalCaseResult = {
  id: string;
  case_name: string;
  prompt: string;
  status: string;
  score: number;
  scores: Record<string, number>;
  checks: Array<{
    name: string;
    category: string;
    passed: boolean;
    score: number;
    details?: Record<string, unknown>;
  }>;
  failure_category: string | null;
  assistant_answer: string | null;
  trace: Record<string, unknown> | null;
  error_type: string | null;
  error_message: string | null;
  conversation_id: string | null;
  agent_run_id: string | null;
  created_at: string;
};

type EvalRunDetail = EvalRunSummary & {
  results: EvalCaseResult[];
};

type EvalSuiteDashboard = {
  suite_name: string;
  runs: EvalRunSummary[];
  latest_run: EvalRunSummary | null;
};

type AdminDashboard = {
  viewer: AuthUser;
  admin_emails_configured: boolean;
  runs: EvalRunSummary[];
  latest_run: EvalRunDetail | null;
  suites: EvalSuiteDashboard[];
};

type AdminDashboardPayload = Omit<AdminDashboard, "suites"> & {
  suites?: EvalSuiteDashboard[];
};

type LoginEvent = {
  id: string;
  user_id: string;
  created_at: string;
};

type UserLoginSummary = {
  user_id: string;
  login_count: number;
  latest_login_at: string | null;
};

type UsersDashboard = {
  logins: LoginEvent[];
  user_login_counts: UserLoginSummary[];
};

function formatDate(value: string | null) {
  if (!value) {
    return "Not completed";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatPercent(value: number | null) {
  if (value === null || Number.isNaN(value)) {
    return "n/a";
  }

  return `${Math.round(value * 100)}%`;
}

function statusLabel(status: string) {
  return status.replace(/_/g, " ");
}

function shortId(value: string | null) {
  if (!value) {
    return "n/a";
  }

  return `${value.slice(0, 8)}...${value.slice(-4)}`;
}

function jsonPreview(value: unknown) {
  if (!value) {
    return "None";
  }

  return JSON.stringify(value, null, 2);
}

function normalizeEvaluationDashboard(
  payload: AdminDashboardPayload,
): AdminDashboard {
  const suites =
    payload.suites && payload.suites.length > 0
      ? payload.suites
      : buildSuiteDashboards(payload.runs, payload.latest_run);

  return {
    ...payload,
    suites,
  };
}

function buildSuiteDashboards(
  runs: EvalRunSummary[],
  latestRun: EvalRunDetail | null,
): EvalSuiteDashboard[] {
  const suiteOrder = ["smoke", "prod"];
  const grouped = new Map<string, EvalRunSummary[]>(
    suiteOrder.map((suiteName) => [suiteName, []]),
  );

  runs.forEach((run) => {
    const suiteRuns = grouped.get(run.suite_name) ?? [];
    suiteRuns.push(run);
    grouped.set(run.suite_name, suiteRuns);
  });

  const suiteNames = [
    ...suiteOrder,
    ...Array.from(grouped.keys())
      .filter((suiteName) => !suiteOrder.includes(suiteName))
      .sort(),
  ];

  return suiteNames.map((suiteName) => {
    const suiteRuns = grouped.get(suiteName) ?? [];
    return {
      suite_name: suiteName,
      runs: suiteRuns,
      latest_run:
        latestRun?.suite_name === suiteName
          ? latestRun
          : suiteRuns[0] ?? null,
    };
  });
}

type EvalCheck = EvalCaseResult["checks"][number];

type EvalCheckGroup = {
  checks: EvalCheck[];
  id: string;
  title: string;
};

function groupedChecks(checks: EvalCheck[]) {
  const groups: EvalCheckGroup[] = [];
  const toolCallGroups = new Map<string, EvalCheckGroup>();

  checks.forEach((check) => {
    const toolCallMatch = check.name.match(/^routing\.tool_call_(\d+)(?:\..+)?$/);

    if (!toolCallMatch) {
      groups.push({
        checks: [check],
        id: check.name,
        title: check.name,
      });
      return;
    }

    const toolCallIndex = toolCallMatch[1];
    const groupId = `routing.tool_call_${toolCallIndex}`;
    let group = toolCallGroups.get(groupId);

    if (!group) {
      group = {
        checks: [],
        id: groupId,
        title: `Tool call ${toolCallIndex}`,
      };
      toolCallGroups.set(groupId, group);
      groups.push(group);
    }

    group.checks.push(check);
  });

  return groups;
}

function AdminDisclosure({
  children,
  defaultOpen = true,
  title,
}: {
  children: ReactNode;
  defaultOpen?: boolean;
  title: string;
}) {
  return (
    <details className="admin-disclosure" open={defaultOpen}>
      <summary>{title}</summary>
      <div className="admin-disclosure-body">{children}</div>
    </details>
  );
}

function startOAuth(provider: "google" | "microsoft") {
  if (!API_URL) {
    return;
  }

  window.location.href = `${API_URL}/auth/${provider}/login?next=/admin`;
}

export default function AdminPage() {
  const [state, setState] = useState<AdminState>("checking");
  const [activeTab, setActiveTab] = useState<AdminTab>("users");
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [usersDashboard, setUsersDashboard] = useState<UsersDashboard | null>(null);
  const [selectedRun, setSelectedRun] = useState<EvalRunDetail | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedSuiteName, setSelectedSuiteName] = useState<string>("smoke");
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [runIsLoading, setRunIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function signOut() {
    try {
      if (API_URL) {
        await fetch(`${API_URL}/auth/logout`, {
          method: "POST",
          credentials: "include",
        });
      }
    } catch {
      // Keep the local sign-out behavior responsive even if the API call fails.
    }

    window.localStorage.removeItem("open-reliability-conversation-id");
    window.dispatchEvent(new Event("polaris-auth-changed"));
    setDashboard(null);
    setUsersDashboard(null);
    setSelectedRun(null);
    setSelectedRunId(null);
    setSelectedSuiteName("smoke");
    setSelectedCaseId(null);
    setState("signed-out");
  }

  const loadRun = useCallback(async (runId: string, signal?: AbortSignal) => {
    if (!API_URL) {
      return;
    }

    setRunIsLoading(true);
    try {
      const response = await fetchWithTimeout(
        `${API_URL}/admin/evaluations/runs/${runId}`,
        {
          credentials: "include",
          signal,
        },
      );
      if (!response.ok) {
        throw new Error("Could not load evaluation run details.");
      }
      const run: EvalRunDetail = await response.json();
      setSelectedRun(run);
      setSelectedRunId(run.id);
      setSelectedSuiteName(run.suite_name);
      setSelectedCaseId(run.results[0]?.id ?? null);
    } finally {
      setRunIsLoading(false);
    }
  }, []);

  const selectSuite = useCallback(
    async (suite: EvalSuiteDashboard) => {
      setSelectedSuiteName(suite.suite_name);

      if (!suite.latest_run) {
        setSelectedRun(null);
        setSelectedRunId(null);
        setSelectedCaseId(null);
        return;
      }

      await loadRun(suite.latest_run.id);
    },
    [loadRun],
  );

  useEffect(() => {
    const requestController = new AbortController();

    async function loadDashboard() {
      if (!API_URL) {
        setState("error");
        setErrorMessage("NEXT_PUBLIC_API_URL is not configured.");
        return;
      }

      try {
        const authResponse = await fetchWithTimeout(`${API_URL}/auth/me`, {
          credentials: "include",
          signal: requestController.signal,
        });
        if (authResponse.status === 401) {
          setState("signed-out");
          return;
        }
        if (!authResponse.ok) {
          throw new Error("Could not check the current session.");
        }

        const [evaluationResponse, usersResponse] = await Promise.all([
          fetchWithTimeout(`${API_URL}/admin/evaluations`, {
            credentials: "include",
            signal: requestController.signal,
          }),
          fetchWithTimeout(`${API_URL}/admin/users`, {
            credentials: "include",
            signal: requestController.signal,
          }),
        ]);

        if (evaluationResponse.status === 403 || usersResponse.status === 403) {
          setState("forbidden");
          return;
        }
        if (!evaluationResponse.ok || !usersResponse.ok) {
          throw new Error("Could not load the admin dashboard.");
        }

        const evaluationPayload = normalizeEvaluationDashboard(
          await evaluationResponse.json(),
        );
        const usersPayload: UsersDashboard = await usersResponse.json();
        const defaultSuite =
          evaluationPayload.suites.find(
            (suite) =>
              suite.latest_run?.id === evaluationPayload.latest_run?.id,
          ) ??
          evaluationPayload.suites.find((suite) => suite.latest_run) ??
          null;
        const defaultRun = evaluationPayload.latest_run;
        setDashboard(evaluationPayload);
        setUsersDashboard(usersPayload);
        setSelectedRun(defaultRun);
        setSelectedRunId(defaultRun?.id ?? null);
        setSelectedSuiteName(
          defaultSuite?.suite_name ?? defaultRun?.suite_name ?? "smoke",
        );
        setSelectedCaseId(defaultRun?.results[0]?.id ?? null);
        setState("authorized");
      } catch (error) {
        if (!requestController.signal.aborted) {
          setState("error");
          setErrorMessage(
            error instanceof Error
              ? error.message
              : "Could not load the admin dashboard.",
          );
        }
      }
    }

    loadDashboard();

    return () => requestController.abort();
  }, []);

  const failedChecks = useMemo(() => {
    if (!selectedRun) {
      return [];
    }

    return selectedRun.results.flatMap((result) =>
      result.checks
        .filter((check) => !check.passed)
        .map((check) => ({
          caseName: result.case_name,
          check,
        })),
    );
  }, [selectedRun]);

  if (state === "checking") {
    return (
      <main className="admin-shell">
        <section className="admin-empty-state">
          <p className="admin-kicker">Admin</p>
          <h1>Checking your session...</h1>
        </section>
      </main>
    );
  }

  if (state === "signed-out") {
    return (
      <main className="admin-shell admin-login-shell">
        <section className="admin-login-panel" aria-labelledby="admin-login-title">
          <Link className="login-back-link" href="/">
            Back to home
          </Link>
          <div className="admin-login-copy">
            <p className="admin-kicker">Admin</p>
            <h1 id="admin-login-title">Sign in to review operations</h1>
            <p>
              Use your Google or Microsoft account to access admin-only login
              activity and evaluation results.
            </p>
          </div>
          <div className="login-actions">
            <button
              className="login-provider-button"
              disabled={!API_URL}
              onClick={() => startOAuth("google")}
              type="button"
            >
              Continue with Google
            </button>
            <button
              className="login-provider-button"
              disabled={!API_URL}
              onClick={() => startOAuth("microsoft")}
              type="button"
            >
              Continue with Microsoft
            </button>
          </div>
        </section>
      </main>
    );
  }

  if (state === "forbidden") {
    return (
      <main className="admin-shell">
        <section className="admin-empty-state">
          <p className="admin-kicker">Admin</p>
          <h1>Admin access required</h1>
          <p>
            Your account is signed in, but it is not included in the configured
            admin email allowlist.
          </p>
        </section>
      </main>
    );
  }

  if (state === "error") {
    return (
      <main className="admin-shell">
        <section className="admin-empty-state">
          <p className="admin-kicker">Admin</p>
          <h1>Dashboard unavailable</h1>
          <p>{errorMessage}</p>
        </section>
      </main>
    );
  }

  return (
    <main className="admin-shell">
      <section className="admin-header">
        <div>
          <p className="admin-kicker">Admin</p>
          <h1>Operations dashboard</h1>
          <p>
            Signed in as {dashboard?.viewer.display_name || dashboard?.viewer.email}.
          </p>
        </div>
        <div className="admin-header-actions">
          <Link className="admin-secondary-link" href="/">
            Homepage
          </Link>
          <button
            className="admin-secondary-link admin-signout-button"
            onClick={signOut}
            type="button"
          >
            Sign out
          </button>
        </div>
      </section>

      <nav className="admin-tabs" aria-label="Admin dashboard sections">
        <button
          aria-pressed={activeTab === "users"}
          className="admin-tab"
          onClick={() => setActiveTab("users")}
          type="button"
        >
          Users
        </button>
        <button
          aria-pressed={activeTab === "evaluations"}
          className="admin-tab"
          onClick={() => setActiveTab("evaluations")}
          type="button"
        >
          Evaluation
        </button>
      </nav>

      {activeTab === "users" ? (
        <UsersTab usersDashboard={usersDashboard} />
      ) : (
        <EvaluationTab
          dashboard={dashboard}
          failedChecks={failedChecks}
          loadRun={loadRun}
          onSelectSuite={selectSuite}
          runIsLoading={runIsLoading}
          selectedCaseId={selectedCaseId}
          selectedRun={selectedRun}
          selectedRunId={selectedRunId}
          selectedSuiteName={selectedSuiteName}
          setSelectedCaseId={setSelectedCaseId}
        />
      )}
    </main>
  );
}

function UsersTab({
  usersDashboard,
}: {
  usersDashboard: UsersDashboard | null;
}) {
  return (
    <div className="admin-users-stack">
      <section className="admin-panel">
        <div className="admin-panel-heading">
          <div>
            <p className="admin-kicker">Users</p>
            <h2>Web logins</h2>
          </div>
        </div>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Login id</th>
                <th>User id</th>
                <th>Date login</th>
              </tr>
            </thead>
            <tbody>
              {(usersDashboard?.logins ?? []).map((login) => (
                <tr key={login.id}>
                  <td>{shortId(login.id)}</td>
                  <td>{shortId(login.user_id)}</td>
                  <td>{formatDate(login.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="admin-panel">
        <div className="admin-panel-heading">
          <div>
            <p className="admin-kicker">Users</p>
            <h2>Login counts</h2>
          </div>
        </div>
        <div className="admin-table-wrap">
          <table className="admin-table admin-table-compact">
            <thead>
              <tr>
                <th>User id</th>
                <th>Logins</th>
                <th>Latest login</th>
              </tr>
            </thead>
            <tbody>
              {(usersDashboard?.user_login_counts ?? []).map((summary) => (
                <tr key={summary.user_id}>
                  <td>{shortId(summary.user_id)}</td>
                  <td>{summary.login_count}</td>
                  <td>{formatDate(summary.latest_login_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function EvaluationTab({
  dashboard,
  failedChecks,
  loadRun,
  onSelectSuite,
  runIsLoading,
  selectedCaseId,
  selectedRun,
  selectedRunId,
  selectedSuiteName,
  setSelectedCaseId,
}: {
  dashboard: AdminDashboard | null;
  failedChecks: Array<{
    caseName: string;
    check: EvalCaseResult["checks"][number];
  }>;
  loadRun: (runId: string) => Promise<void>;
  onSelectSuite: (suite: EvalSuiteDashboard) => Promise<void>;
  runIsLoading: boolean;
  selectedCaseId: string | null;
  selectedRun: EvalRunDetail | null;
  selectedRunId: string | null;
  selectedSuiteName: string;
  setSelectedCaseId: (caseId: string) => void;
}) {
  const selectedCase = selectedRun?.results.find(
    (result) => result.id === selectedCaseId,
  ) ?? selectedRun?.results[0] ?? null;
  const selectedSuite = dashboard?.suites.find(
    (suite) => suite.suite_name === selectedSuiteName,
  ) ?? dashboard?.suites[0] ?? null;
  const visibleRuns = selectedSuite?.runs ?? dashboard?.runs ?? [];

  return (
    <>
      <section className="admin-suite-grid" aria-label="Evaluation suites">
        {(dashboard?.suites ?? []).map((suite) => (
          <button
            aria-pressed={selectedSuiteName === suite.suite_name}
            className="admin-suite-card"
            key={suite.suite_name}
            onClick={() => {
              void onSelectSuite(suite);
            }}
            type="button"
          >
            <span>{suite.suite_name === "prod" ? "Prod test" : "Smoke test"}</span>
            <strong>{formatPercent(suite.latest_run?.aggregate_score ?? null)}</strong>
            <small>
              {suite.latest_run
                ? `${suite.latest_run.passed_count}/${suite.latest_run.case_count} passed`
                : "No runs yet"}
            </small>
          </button>
        ))}
      </section>

      <section className="admin-metrics-grid" aria-label="Selected evaluation summary">
        <article className="admin-metric">
          <span>Selected score</span>
          <strong>{formatPercent(selectedRun?.aggregate_score ?? null)}</strong>
        </article>
        <article className="admin-metric">
          <span>Passed</span>
          <strong>{selectedRun?.passed_count ?? 0}</strong>
        </article>
        <article className="admin-metric">
          <span>Failed</span>
          <strong>{selectedRun?.failed_count ?? 0}</strong>
        </article>
        <article className="admin-metric">
          <span>Suite runs</span>
          <strong>{visibleRuns.length}</strong>
        </article>
      </section>

      {!selectedRun ? (
        <section className="admin-empty-state">
          <h2>No evaluation runs yet</h2>
          <p>
            Run the selected suite from the API app to populate this dashboard.
          </p>
          <code>
            .venv/bin/python -m app.cli.run_evaluation --suite {selectedSuiteName}
          </code>
        </section>
      ) : (
        <div className="admin-dashboard-grid">
          <section className="admin-panel">
            <div className="admin-panel-heading">
              <div>
                <p className="admin-kicker">Selected run</p>
                <h2>{selectedRun.suite_name}</h2>
              </div>
              <span className={`admin-status admin-status-${selectedRun.status}`}>
                {statusLabel(selectedRun.status)}
              </span>
            </div>
            <dl className="admin-run-facts">
              <div>
                <dt>Run id</dt>
                <dd>{shortId(selectedRun.id)}</dd>
              </div>
              <div>
                <dt>Model</dt>
                <dd>{selectedRun.model}</dd>
              </div>
              <div>
                <dt>Dataset</dt>
                <dd>{selectedRun.dataset_version || "n/a"}</dd>
              </div>
              <div>
                <dt>Git commit</dt>
                <dd>{selectedRun.git_commit ? shortId(selectedRun.git_commit) : "n/a"}</dd>
              </div>
              <div>
                <dt>Started</dt>
                <dd>{formatDate(selectedRun.started_at)}</dd>
              </div>
              <div>
                <dt>Completed</dt>
                <dd>{formatDate(selectedRun.completed_at)}</dd>
              </div>
            </dl>

            <div className="admin-json-panel">
              <h3>Run metadata</h3>
              <pre>{jsonPreview(selectedRun.run_metadata)}</pre>
            </div>

            <div className="admin-case-list">
              {selectedRun.results.map((result) => (
                <button
                  aria-pressed={selectedCase?.id === result.id}
                  className="admin-case-row admin-case-button"
                  key={result.id}
                  onClick={() => setSelectedCaseId(result.id)}
                  type="button"
                >
                  <div>
                    <h3>{result.case_name}</h3>
                    <p>{result.prompt}</p>
                    <p>
                      Agent run {shortId(result.agent_run_id)} · Conversation{" "}
                      {shortId(result.conversation_id)}
                    </p>
                  </div>
                  <div className="admin-case-score">
                    <span className={`admin-status admin-status-${result.status}`}>
                      {statusLabel(result.status)}
                    </span>
                    <strong>{formatPercent(result.score)}</strong>
                  </div>
                </button>
              ))}
            </div>
          </section>

          <section className="admin-panel admin-troubleshooting-panel">
            <div className="admin-panel-heading">
              <div>
                <p className="admin-kicker">Troubleshooting</p>
                <h2>{selectedCase?.case_name ?? "Test result"}</h2>
              </div>
            </div>
            {!selectedCase ? (
              <p className="admin-muted">Select a test to inspect its result.</p>
            ) : (
              <div className="admin-test-detail">
                <AdminDisclosure title="Case context">
                  <div className="admin-test-summary">
                    <span className={`admin-status admin-status-${selectedCase.status}`}>
                      {statusLabel(selectedCase.status)}
                    </span>
                    <strong>{formatPercent(selectedCase.score)}</strong>
                  </div>
                  <p className="admin-muted">{selectedCase.prompt}</p>
                  <dl className="admin-run-facts admin-run-facts-single">
                    <div>
                      <dt>Agent run</dt>
                      <dd>{shortId(selectedCase.agent_run_id)}</dd>
                    </div>
                    <div>
                      <dt>Conversation</dt>
                      <dd>{shortId(selectedCase.conversation_id)}</dd>
                    </div>
                    <div>
                      <dt>Failure category</dt>
                      <dd>{selectedCase.failure_category ?? "None"}</dd>
                    </div>
                  </dl>
                </AdminDisclosure>
                <AdminDisclosure title="Evaluation checks">
                  <div className="admin-failed-checks">
                    {groupedChecks(selectedCase.checks).map((group) => {
                      const groupPassed = group.checks.every((check) => check.passed);

                      return (
                        <article
                          className={
                            groupPassed
                              ? "admin-check-card"
                              : "admin-failed-check"
                          }
                          key={group.id}
                        >
                          <div className="admin-check-heading">
                            <h3>{group.title}</h3>
                            <span>{groupPassed ? "passed" : "failed"}</span>
                          </div>
                          <div className="admin-check-sections">
                            {group.checks.map((check) => (
                              <details
                                className="admin-check-section"
                                key={check.name}
                                open={!check.passed}
                              >
                                <summary>
                                  <strong>{check.name}</strong>
                                  <span>{check.passed ? "passed" : "failed"}</span>
                                </summary>
                                <p>{check.category}</p>
                                <pre>{jsonPreview(check.details)}</pre>
                              </details>
                            ))}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </AdminDisclosure>
                <AdminDisclosure defaultOpen={false} title="Trace">
                  <div className="admin-json-panel">
                    <pre>{jsonPreview(selectedCase.trace)}</pre>
                  </div>
                </AdminDisclosure>
                <AdminDisclosure defaultOpen={false} title="Assistant answer">
                  <div className="admin-json-panel">
                    <pre>{selectedCase.assistant_answer || "None"}</pre>
                  </div>
                </AdminDisclosure>
                {failedChecks.length > 0 ? (
                  <AdminDisclosure defaultOpen={false} title="Run failed-check index">
                    <div className="admin-json-panel">
                      <pre>
                        {jsonPreview(
                          failedChecks.map(({ caseName, check }) => ({
                            caseName,
                            check: check.name,
                            category: check.category,
                          })),
                        )}
                      </pre>
                    </div>
                  </AdminDisclosure>
                ) : null}
              </div>
            )}
          </section>
        </div>
      )}

      <section className="admin-panel">
        <div className="admin-panel-heading">
          <div>
            <p className="admin-kicker">History</p>
            <h2>Recent runs</h2>
          </div>
          {runIsLoading ? <span className="admin-muted">Loading run...</span> : null}
        </div>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Suite</th>
                <th>Status</th>
                <th>Score</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Model</th>
                <th>Metadata</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {visibleRuns.map((run) => (
                <tr
                  className={
                    selectedRunId === run.id
                      ? "admin-selected-row"
                      : undefined
                  }
                  key={run.id}
                >
                  <td>
                    <button
                      aria-pressed={selectedRunId === run.id}
                      className="admin-table-button"
                      onClick={() => loadRun(run.id)}
                      type="button"
                    >
                      {run.suite_name}
                    </button>
                  </td>
                  <td>{statusLabel(run.status)}</td>
                  <td>{formatPercent(run.aggregate_score)}</td>
                  <td>{run.passed_count}</td>
                  <td>{run.failed_count}</td>
                  <td>{run.model}</td>
                  <td>{run.run_metadata ? "Yes" : "None"}</td>
                  <td>{formatDate(run.started_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
