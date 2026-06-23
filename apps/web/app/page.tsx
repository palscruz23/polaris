import Link from "next/link";

type SpecialistAgent = {
  id: string;
  title: string;
  purpose: string;
  status?: "future";
};

const specialistAgents: readonly SpecialistAgent[] = [
  {
    id: "master-data",
    title: "Master Data Agent",
    purpose:
      "Searches and filters the stored equipment master so reliability workflows can identify assets and use trusted equipment context.",
  },
  {
    id: "defect-elimination",
    title: "Defect Elimination Agent",
    purpose:
      "Converts reliability issues into structured investigations, including problem statements, hypotheses, RCA plans, and corrective actions.",
  },
  {
    id: "strategy",
    title: "Maintenance Strategy Agent",
    purpose:
      "Reviews and optimizes maintenance strategies by checking PM effectiveness, failure mode coverage, OEM guidance, and strategy gaps.",
  },
  {
    id: "improvement",
    title: "Reliability Improvement Agent",
    status: "future",
    purpose:
      "Future workflow for converting engineering findings into ranked opportunities, cost-benefit context, action plans, and reliability roadmaps.",
  },
];

const flowNodes = {
  userRequest: {
    id: "user-request",
    title: "User request",
    purpose:
      "A reliability question starts the current chat flow. Uploaded datasets and improvement workflows are planned next steps.",
  },
  managerIntake: {
    id: "manager-intake",
    title: "Reliability Agent",
    purpose:
      "The only agent visible to the user. It reviews each request, selects the required specialist agents, and coordinates their analysis.",
  },
  managerReview: {
    id: "manager-review",
    title: "Reliability Agent",
    purpose:
      "Reviews structured specialist findings, consolidates the evidence, and produces one user-facing reliability recommendation.",
  },
  finalResponse: {
    id: "final-response",
    title: "Final response",
    purpose:
      "A reliability answer or next-step plan grounded in the available conversation context and specialist findings.",
  },
};

const purposeItems = [
  flowNodes.managerIntake,
  ...specialistAgents,
  flowNodes.managerReview,
];

const features = [
  {
    title: "Reliability Agent",
    description:
      "Reliability chat with persistent conversations, message history, memory updates, and specialist orchestration.",
  },
  {
    title: "Work Order Intelligence",
    description:
      "Analysis for surfacing bad actors, repeat failures, downtime patterns, and cost drivers from maintenance history.",
  },
  {
    title: "Equipment Intelligence",
    description:
      "Asset-level summaries that combine history, strategy, known failure modes, and improvement options.",
  },
  {
    title: "Actionable Recommendations",
    description:
      "Outputs for prioritized reliability actions with supporting evidence and practical next steps.",
  },
  {
    title: "Data Mapping Wizard",
    status: "future" as const,
    description:
      "Planned workflow for guiding uploaded work order, strategy, and equipment data into a consistent reliability model.",
  },
  {
    title: "Reliability Knowledge Base",
    status: "future" as const,
    description:
      "Planned retrieval layer for indexing FMEAs, RCA reports, OEM manuals, and site standards.",
  },
];

const heroBenefits = [
  {
    title: "Keep reliability context together",
    description:
      "Persistent conversations retain the engineering thread across follow-up questions and planning sessions.",
  },
  {
    title: "Turn analysis into next actions",
    description:
      "Planned workflows connect data review, defect elimination, strategy checks, and improvement planning.",
  },
  {
    title: "Grow capability in practical stages",
    description:
      "Each product capability can be designed, tested, and released without hiding what is available today.",
  },
];

const footerLinks = [
  {
    label: "GitHub",
    href: "https://github.com/palscruz23/open-reliability",
  },
  {
    label: "Report an issue",
    href: "https://github.com/palscruz23/open-reliability/issues/new",
  },
  {
    label: "Apache 2.0",
    href: "https://github.com/palscruz23/open-reliability/blob/main/LICENSE",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <section className="hero-section border-b border-[var(--border)]">
        <div className="hero-container mx-auto flex max-w-6xl flex-col gap-10 px-6 py-10 md:gap-10 md:px-8 md:py-14">
          <nav className="app-nav flex items-center justify-between gap-6">
            <Link href="/" className="brand-link text-lg font-semibold">
              <span>Open Reliability</span>
            </Link>
          </nav>

          <div className="grid gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-end">
            <div className="max-w-3xl">
              <h1 className="text-4xl font-semibold leading-[1.05] text-[var(--heading)] md:text-6xl">
                Open Reliability Copilot
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-[var(--muted)]">
                A reliability engineering workspace with persistent
                conversations, defect elimination analysis, and maintenance
                strategy review coordinated through the Reliability Agent.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  className="button button-primary"
                  href="/chat-with-reliability"
                >
                  Chat with Reliability Agent
                </Link>
                <Link className="button button-secondary" href="#capability-roadmap">
                  Explore capability roadmap
                </Link>
              </div>
            </div>

            <div className="benefit-panel" aria-label="Open Reliability benefits">
              <p className="panel-label">Why it matters</p>
              {heroBenefits.map((benefit) => (
                <article className="benefit-item" key={benefit.title}>
                  <h2>{benefit.title}</h2>
                  <p>{benefit.description}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="architecture-section" id="agent-workflow">
        <div className="architecture-container mx-auto max-w-6xl px-6 py-14 md:px-8 md:py-12">
        <div className="section-heading">
          <h2>Agent Workflow</h2>
          <p>
            The Reliability Agent is the only user-visible agent. It coordinates
            implemented specialist workflows for defect elimination and
            maintenance strategy review, with additional specialists added in
            practical stages.
          </p>
        </div>

        <div className="agent-architecture-layout">
          <div className="flow-chart" aria-label="Reliability agent flow chart">
            <article className="flow-node flow-node-user-request">
              <span className="flow-node-index">1</span>
              <h3>{flowNodes.userRequest.title}</h3>
            </article>

            <span className="flow-connector flow-connector-intake" aria-hidden="true">
              →
            </span>

            <article className="flow-node flow-node-manager flow-node-manager-intake" tabIndex={0}>
              <span className="flow-node-index">2</span>
              <h3>{flowNodes.managerIntake.title}</h3>
            </article>

            <span className="flow-connector flow-connector-spawn" aria-hidden="true">
              coordinates
            </span>

            <div className="spawn-stack" aria-label="Specialist agents">
              {specialistAgents.map((agent, index) => (
                <article
                  className={`flow-node flow-node-specialist flow-node-${agent.id}`}
                  key={agent.title}
                  tabIndex={0}
                >
                  <span className="flow-node-index">{index + 3}</span>
                  {agent.status === "future" ? (
                    <span className="flow-node-status">Future</span>
                  ) : null}
                  <h3>{agent.title}</h3>
                </article>
              ))}
            </div>

            <span className="flow-connector flow-connector-review" aria-hidden="true">
              →
            </span>

            <article className="flow-node flow-node-manager flow-node-manager-review" tabIndex={0}>
              <span className="flow-node-index">7</span>
              <h3>{flowNodes.managerReview.title}</h3>
            </article>

            <span className="flow-connector flow-connector-final" aria-hidden="true">
              →
            </span>

            <aside className="purpose-panel" aria-label="Agent purpose">
              <p className="panel-label">Purpose</p>
              {purposeItems.map((item) => (
                <div className={`purpose-copy purpose-${item.id}`} key={item.id}>
                  <h3>{item.title}</h3>
                  <p>{item.purpose}</p>
                </div>
              ))}
            </aside>

            <article className="flow-node flow-node-final-response" tabIndex={0}>
              <span className="flow-node-index">8</span>
              <h3>{flowNodes.finalResponse.title}</h3>
            </article>
          </div>
        </div>
        </div>
      </section>

      <section className="feature-section border-t border-[var(--border)]" id="capability-roadmap">
        <div className="mx-auto max-w-6xl px-6 py-14 md:px-8 md:py-20">
          <div className="section-heading">
            <h2>Capability roadmap</h2>
            <p>
              These product capabilities define how Open Reliability will grow
              from chat into a practical reliability engineering workspace.
              Each capability will be designed and shipped one workflow at a
              time.
            </p>
          </div>

          <div className="feature-grid">
            {features.map((feature) => (
              <article className="feature-card" key={feature.title}>
                {"status" in feature && feature.status === "future" ? (
                  <span className="feature-card-status">Future</span>
                ) : null}
                <span className="feature-card-title">{feature.title}</span>
                <span className="feature-card-description">{feature.description}</span>
              </article>
            ))}
          </div>
        </div>
      </section>

      <footer className="home-footer">
        <div className="home-footer-container mx-auto max-w-6xl px-6 py-4 md:px-8">
          <Link href="/" className="home-footer-brand">
            Open Reliability
          </Link>
          <p className="home-footer-status">Open for demo / collab</p>
          <nav className="home-footer-links" aria-label="Footer">
            {footerLinks.map((link, index) => (
              <span className="home-footer-link-item" key={link.label}>
                {index > 0 ? (
                  <span className="home-footer-separator" aria-hidden="true">
                    ·
                  </span>
                ) : null}
                <a
                  className="home-footer-link"
                  href={link.href}
                  rel="noreferrer"
                  target="_blank"
                >
                  {link.label}
                </a>
              </span>
            ))}
          </nav>
        </div>
      </footer>
    </main>
  );
}
