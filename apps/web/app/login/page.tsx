"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;
const DEFAULT_NEXT_PATH = "/chat-with-reliability";

function getSafeNextPath() {
  if (typeof window === "undefined") {
    return DEFAULT_NEXT_PATH;
  }

  const requestedPath = new URLSearchParams(window.location.search).get("next");
  if (
    requestedPath &&
    requestedPath.startsWith("/") &&
    !requestedPath.startsWith("//")
  ) {
    return requestedPath;
  }

  return DEFAULT_NEXT_PATH;
}

function ProviderIcon({ provider }: { provider: "google" | "microsoft" }) {
  if (provider === "google") {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M21.6 12.2c0-.7-.1-1.3-.2-1.9H12v3.6h5.4a4.6 4.6 0 0 1-2 3v2.5h3.2c1.9-1.7 3-4.2 3-7.2Z" />
        <path d="M12 22c2.7 0 5-0.9 6.6-2.5l-3.2-2.5c-.9.6-2 .9-3.4.9a6 6 0 0 1-5.6-4.1H3.1v2.6A10 10 0 0 0 12 22Z" />
        <path d="M6.4 13.8a6 6 0 0 1 0-3.6V7.6H3.1a10 10 0 0 0 0 8.8l3.3-2.6Z" />
        <path d="M12 6.1c1.5 0 2.8.5 3.8 1.5l2.9-2.9A9.7 9.7 0 0 0 12 2 10 10 0 0 0 3.1 7.6l3.3 2.6A6 6 0 0 1 12 6.1Z" />
      </svg>
    );
  }

  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M3 3h8.5v8.5H3Z" />
      <path d="M12.5 3H21v8.5h-8.5Z" />
      <path d="M3 12.5h8.5V21H3Z" />
      <path d="M12.5 12.5H21V21h-8.5Z" />
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  useEffect(() => {
    const requestController = new AbortController();

    async function checkSession() {
      if (!API_URL) {
        setIsCheckingSession(false);
        return;
      }

      try {
        const response = await fetch(`${API_URL}/auth/me`, {
          credentials: "include",
          signal: requestController.signal,
        });
        if (response.ok) {
          router.replace(getSafeNextPath());
          return;
        }
      } catch {
        // Stay on login; the user can retry through the provider buttons.
      }

      if (!requestController.signal.aborted) {
        setIsCheckingSession(false);
      }
    }

    checkSession();

    return () => requestController.abort();
  }, [router]);

  function startOAuth(provider: "google" | "microsoft") {
    if (!API_URL) {
      return;
    }

    const nextPath = encodeURIComponent(getSafeNextPath());
    window.location.href = `${API_URL}/auth/${provider}/login?next=${nextPath}`;
  }

  return (
    <main className="login-shell">
      <section className="login-panel" aria-labelledby="login-heading">
        <Link className="login-back-link" href="/">
          Back to home
        </Link>
        <Image
          alt="Polaris"
          className="login-title-image"
          height={149}
          priority
          src="/brand/polaris-word.png"
          width={1285}
        />
        <div className="login-copy">
          <h1 id="login-heading">Sign in to continue</h1>
          <p>
            Use your Google or Microsoft account to keep reliability
            conversations private to your session.
          </p>
        </div>
        <div className="login-actions" aria-busy={isCheckingSession}>
          <button
            className="login-provider-button"
            disabled={isCheckingSession || !API_URL}
            onClick={() => startOAuth("google")}
            type="button"
          >
            <ProviderIcon provider="google" />
            Continue with Google
          </button>
          <button
            className="login-provider-button"
            disabled={isCheckingSession || !API_URL}
            onClick={() => startOAuth("microsoft")}
            type="button"
          >
            <ProviderIcon provider="microsoft" />
            Continue with Microsoft
          </button>
        </div>
        {!API_URL ? (
          <p className="login-error">NEXT_PUBLIC_API_URL is not configured.</p>
        ) : null}
      </section>
    </main>
  );
}
