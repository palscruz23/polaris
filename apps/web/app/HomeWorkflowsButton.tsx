import Link from "next/link";

export default function HomeWorkflowsButton() {
  return (
    <Link className="button button-secondary" href="/workflows">
      Workflows
    </Link>
  );
}
