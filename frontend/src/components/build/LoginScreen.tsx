"use client";

import { useState } from "react";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "@/lib/auth";
import { SparklesIcon } from "./icons";

export function LoginScreen() {
  const { loginWithGoogle } = useAuth();
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="flex min-h-dvh items-center justify-center bg-ui-canvas p-6 font-ui text-ui-text">
      <div className="panel relative w-full max-w-sm overflow-hidden p-8 text-center">
        <div
          className="brand-field pointer-events-none absolute inset-0"
          aria-hidden
        />

        <div className="relative flex flex-col items-center">
          <span className="brand-gradient flex h-12 w-12 items-center justify-center rounded-2xl text-white shadow-[0_8px_24px_rgba(79,70,229,0.28)]">
            <SparklesIcon className="h-5 w-5" />
          </span>

          <h1 className="mt-5 text-xl font-semibold tracking-tight">
            Magic Landing Pages
          </h1>
          <p className="mt-2 text-sm leading-6 text-ui-muted">
            Sign in to build pages by voice and come back to them later.
          </p>

          <div className="mt-7 flex justify-center">
            <GoogleLogin
              onSuccess={async (credential) => {
                setError(null);
                if (!credential.credential) {
                  setError("Google returned no credential.");
                  return;
                }
                try {
                  await loginWithGoogle(credential.credential);
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Sign-in failed.");
                }
              }}
              onError={() =>
                setError("Google sign-in failed. Please try again.")
              }
              shape="pill"
              text="continue_with"
            />
          </div>

          {error && (
            <p className="mt-4 text-sm text-ui-danger" role="alert">
              {error}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
