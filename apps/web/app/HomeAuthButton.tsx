"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

type AuthState = "checking" | "signed-in" | "signed-out";
type AuthUser = {
  email: string;
  display_name: string | null;
};

function firstNameForUser(user: AuthUser) {
  const sourceName = user.display_name?.trim() || user.email.split("@")[0];
  const firstName = sourceName.split(/\s+/)[0];

  return firstName || "there";
}

export default function HomeAuthButton() {
  const [authState, setAuthState] = useState<AuthState>("checking");
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const requestController = new AbortController();

    async function checkSession() {
      if (!API_URL) {
        setAuthState("signed-out");
        return;
      }

      try {
        const response = await fetch(`${API_URL}/auth/me`, {
          credentials: "include",
          signal: requestController.signal,
        });
        if (response.ok) {
          const currentUser: AuthUser = await response.json();
          setUser(currentUser);
          setAuthState("signed-in");
        } else {
          setUser(null);
          setAuthState("signed-out");
        }
      } catch {
        if (!requestController.signal.aborted) {
          setUser(null);
          setAuthState("signed-out");
        }
      }
    }

    checkSession();

    return () => requestController.abort();
  }, []);

  async function signOut() {
    try {
      if (API_URL) {
        await fetch(`${API_URL}/auth/logout`, {
          method: "POST",
          credentials: "include",
        });
      }
    } catch {
      // The homepage should still return to the signed-out state if logout fails.
    }
    window.localStorage.removeItem("open-reliability-conversation-id");
    setUser(null);
    setAuthState("signed-out");
  }

  if (authState === "signed-in") {
    return (
      <div className="nav-auth-signed-in">
        <span className="nav-auth-greeting">
          Hi {firstNameForUser(user ?? { email: "", display_name: null })}!
        </span>
        <button
          className="nav-auth-link nav-auth-link-signed-in"
          onClick={signOut}
          type="button"
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <Link
      aria-disabled={authState === "checking" ? "true" : undefined}
      className="nav-auth-link nav-auth-link-signed-out"
      href="/login?next=/"
    >
      Sign in
    </Link>
  );
}
