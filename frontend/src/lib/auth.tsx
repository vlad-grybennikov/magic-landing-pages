"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

const BASE_URL =
  process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? "http://localhost:8000";

export const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";

export const SIGNED_OUT = "mlp:signed-out";

const ACCESS_KEY = "mlp.accessToken";
const REFRESH_KEY = "mlp.refreshToken";

export interface AuthUser {
  id: string;
  email: string;
  name?: string | null;
  picture?: string | null;
}

interface AuthValue {
  user: AuthUser | null;
  isLoading: boolean;
  required: boolean;
  loginWithGoogle: (idToken: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | undefined>(undefined);

let accessToken: string | null = null;

export function authHeaders(): Record<string, string> {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
}

function store(tokens: { accessToken: string; refreshToken: string }) {
  accessToken = tokens.accessToken;
  try {
    localStorage.setItem(ACCESS_KEY, tokens.accessToken);
    localStorage.setItem(REFRESH_KEY, tokens.refreshToken);
  } catch {
  }
}

function forget() {
  accessToken = null;
  try {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  } catch {
  }
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail?.message ?? `Sign-in failed (${res.status}).`);
  }
  return res.json();
}

export async function refreshAccess(): Promise<boolean> {
  const refreshToken = (() => {
    try {
      return localStorage.getItem(REFRESH_KEY);
    } catch {
      return null;
    }
  })();
  if (!refreshToken) return false;

  try {
    store(
      await post<{ accessToken: string; refreshToken: string }>("/auth/refresh", {
        refreshToken,
      }),
    );
    return true;
  } catch {
    forget();
    window.dispatchEvent(new Event(SIGNED_OUT));
    return false;
  }
}

async function refresh(): Promise<AuthUser | null> {
  return (await refreshAccess()) ? me() : null;
}

async function me(): Promise<AuthUser | null> {
  const res = await fetch(`${BASE_URL}/auth/me`, { headers: authHeaders() });
  if (!res.ok) return null;
  return res.json();
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [required, setRequired] = useState(!!GOOGLE_CLIENT_ID);
  const restored = useRef(false);

  useEffect(() => {
    if (restored.current) return;
    restored.current = true;

    const restore = async () => {
      try {
        const config = await fetch(`${BASE_URL}/auth/config`).then((r) => r.json());
        setRequired(!!config.enabled);

        if (!config.enabled) {
          setUser(await me());
          return;
        }

        accessToken = localStorage.getItem(ACCESS_KEY);
        setUser((accessToken ? await me() : null) ?? (await refresh()));
      } catch {
        forget();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    restore();
  }, []);

  useEffect(() => {
    const onSignedOut = () => setUser(null);
    window.addEventListener(SIGNED_OUT, onSignedOut);
    return () => window.removeEventListener(SIGNED_OUT, onSignedOut);
  }, []);

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const data = await post<{
      user: AuthUser;
      accessToken: string;
      refreshToken: string;
    }>("/auth/google", { idToken });
    store(data);
    setUser(data.user);
  }, []);

  const logout = useCallback(() => {
    forget();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, required, loginWithGoogle, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
