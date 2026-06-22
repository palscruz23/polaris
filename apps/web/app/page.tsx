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

const socialLinks = [
  {
    label: "Gmail",
    href: "https://mail.google.com/mail/?view=cm&fs=1&to=poljohncruz@gmail.com",
    icon: (
      <svg aria-hidden="true" fill="none" height="20" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24" width="20">
        <path d="M4.75 6.25h14.5A1.75 1.75 0 0 1 21 8v8a1.75 1.75 0 0 1-1.75 1.75H4.75A1.75 1.75 0 0 1 3 16V8a1.75 1.75 0 0 1 1.75-1.75Z" />
        <path d="m4.35 7.15 7.65 6.1 7.65-6.1" />
        <path d="m4.5 17 5.45-5" />
        <path d="m19.5 17-5.45-5" />
      </svg>
    ),
  },
  {
    label: "LinkedIn",
    href: "https://www.linkedin.com/in/poljohncruz/",
    icon: (
      <svg aria-hidden="true" fill="none" height="20" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24" width="20">
        <path d="M7.35 9.25v8.5" />
        <path d="M7.35 6.35v.05" />
        <path d="M11.2 17.75v-8.5" />
        <path d="M11.2 12.85c.52-2.48 5.45-3.06 5.45 1.4v3.5" />
        <path d="M5.25 3.75h13.5A1.5 1.5 0 0 1 20.25 5.25v13.5a1.5 1.5 0 0 1-1.5 1.5H5.25a1.5 1.5 0 0 1-1.5-1.5V5.25a1.5 1.5 0 0 1 1.5-1.5Z" />
      </svg>
    ),
  },
  {
    label: "GitHub",
    href: "https://github.com/palscruz23",
    icon: (
      <svg aria-hidden="true" fill="none" height="20" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24" width="20">
        <path d="M10 19.5c-4.6 1.4-4.6-2.3-6.5-2.8" />
        <path d="M14 22v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 18 4.77 5.07 5.07 0 0 0 17.91 2S16.73 1.65 14 3.48a13.38 13.38 0 0 0-7 0C4.27 1.65 3.09 2 3.09 2A5.07 5.07 0 0 0 3 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 7 18.13V22" />
      </svg>
    ),
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
            <div className="contact-links">
              <span className="contact-links-label">Contact for demo</span>
              <div className="social-links" aria-label="Open Reliability contact links">
                {socialLinks.map((link) => (
                  <a
                    aria-label={link.label}
                    className="social-link inline-flex h-11 w-11 items-center justify-center rounded-lg border border-sky-200/35 bg-slate-950 text-white shadow-lg"
                    href={link.href}
                    key={link.label}
                    rel="noreferrer"
                    target="_blank"
                    title={link.label}
                  >
                    {link.icon}
                  </a>
                ))}
              </div>
            </div>
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
                <Link className="button button-primary" href="/features/reliability-agent-team">
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
    </main>
  );
}
