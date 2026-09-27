"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";
import { AuthProvider, GOOGLE_CLIENT_ID } from "@/lib/auth";

export function Providers({ children }: { children: React.ReactNode }) {
  if (!GOOGLE_CLIENT_ID) return <AuthProvider>{children}</AuthProvider>;

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>{children}</AuthProvider>
    </GoogleOAuthProvider>
  );
}
