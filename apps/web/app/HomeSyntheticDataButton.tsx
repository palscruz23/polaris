import Link from "next/link";

export default function HomeSyntheticDataButton() {
  return (
    <Link className="button button-secondary" href="/view-existing-data">
      View synthetic data
    </Link>
  );
}
