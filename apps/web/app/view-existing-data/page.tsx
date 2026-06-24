import Link from "next/link";

import DataTableBrowser from "./DataTableBrowser";

export default function ViewExistingDataPage() {
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
