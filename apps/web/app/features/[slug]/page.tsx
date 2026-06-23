import Link from "next/link";
import { notFound, redirect } from "next/navigation";

const featurePages: Record<
  string,
  {
    title: string;
    description: string;
  }
> = {
  "data-mapping-wizard": {
    title: "Data Mapping Wizard",
    description:
      "A guided workflow for mapping uploaded plant data into the reliability data model.",
  },
  "work-order-intelligence": {
    title: "Work Order Intelligence",
    description:
      "Analysis tools for identifying bad actors, repeat failures, downtime trends, and maintenance cost drivers.",
  },
  "reliability-knowledge-base": {
    title: "Reliability Knowledge Base",
    description:
      "A searchable engineering repository for FMEAs, RCA reports, OEM manuals, and site standards.",
  },
  "reliability-agent-team": {
    title: "Reliability Agent",
    description:
      "The current reliability chat experience with persistent conversations, message history, and memory updates.",
  },
  "equipment-intelligence": {
    title: "Equipment Intelligence",
    description:
      "Asset-level reliability views that connect history, strategy, failure modes, and improvement opportunities.",
  },
  "actionable-recommendations": {
    title: "Actionable Recommendations",
    description:
      "Prioritized reliability actions with evidence, context, and practical next steps for engineering teams.",
  },
};

export default async function FeaturePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const feature = featurePages[slug];

  if (!feature) {
    notFound();
  }

  if (slug === "reliability-agent-team") {
    redirect("/chat-with-reliability");
  }

  return (
    <main className="min-h-screen bg-[var(--background)] px-6 py-10 text-[var(--foreground)] md:px-8">
      <section className="mx-auto max-w-4xl">
        <Link className="back-link" href="/">
          Back to home
        </Link>
        <div className="placeholder-page">
          <p className="panel-label">Feature placeholder</p>
          <h1>{feature.title}</h1>
          <p>{feature.description}</p>
          <div className="placeholder-note">
            Detailed workflow, data states, and screen design will be decided
            when we implement this feature.
          </div>
        </div>
      </section>
    </main>
  );
}
