"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export default function HomeSyntheticDataButton() {
  const [isSignedIn, setIsSignedIn] = useState(false);

  useEffect(() => {
    const requestController = new AbortController();

    async function checkSession() {
      if (!API_URL) {
        return;
      }

      try {
        const response = await fetch(`${API_URL}/auth/me`, {
          credentials: "include",
          signal: requestController.signal,
        });
        setIsSignedIn(response.ok);
      } catch {
        if (!requestController.signal.aborted) {
          setIsSignedIn(false);
        }
      }
    }

    checkSession();
    function handleAuthChange() {
      setIsSignedIn(false);
    }
    window.addEventListener("polaris-auth-changed", handleAuthChange);

    return () => {
      requestController.abort();
      window.removeEventListener("polaris-auth-changed", handleAuthChange);
    };
  }, []);

  if (!isSignedIn) {
    return null;
  }

  return (
    <Link className="button button-secondary" href="/view-existing-data">
      View synthetic data
    </Link>
  );
}
