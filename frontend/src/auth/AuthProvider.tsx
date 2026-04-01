import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import type { Session, User } from "@supabase/supabase-js";

import { setApiAccessToken } from "../api";
import { getSupabaseClient } from "../lib/supabase";

type EmailUpdateResult = {
  currentEmail: string | null;
  pendingEmail: string | null;
};

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  authError: string | null;
  sendMagicLink: (email: string) => Promise<void>;
  signInWithPassword: (email: string, password: string) => Promise<void>;
  signUpWithPassword: (email: string, password: string) => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
  updateEmail: (email: string) => Promise<EmailUpdateResult>;
  updatePassword: (password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    let supabase;
    try {
      supabase = getSupabaseClient();
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Supabase auth is not configured.");
      setIsLoading(false);
      return;
    }
    let active = true;

    void supabase.auth.getSession().then(({ data }) => {
      if (!active) {
        return;
      }
      setSession(data.session ?? null);
      setUser(data.session?.user ?? null);
      setApiAccessToken(data.session?.access_token ?? null);
      setAuthError(null);
      setIsLoading(false);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession ?? null);
      setUser(nextSession?.user ?? null);
      setApiAccessToken(nextSession?.access_token ?? null);
      setAuthError(null);
      setIsLoading(false);
    });

    return () => {
      active = false;
      subscription.subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      session,
      isLoading,
      isAuthenticated: !!session?.access_token,
      authError,
      sendMagicLink: async (email: string) => {
        let supabase;
        try {
          supabase = getSupabaseClient();
        } catch (error) {
          throw new Error(error instanceof Error ? error.message : "Supabase auth is not configured.");
        }
        const emailRedirectTo = `${window.location.origin}/auth/callback`;
        const { error } = await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo } });
        if (error) {
          throw error;
        }
      },
      signInWithPassword: async (email: string, password: string) => {
        let supabase;
        try {
          supabase = getSupabaseClient();
        } catch (error) {
          throw new Error(error instanceof Error ? error.message : "Supabase auth is not configured.");
        }
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) {
          throw error;
        }
      },
      signUpWithPassword: async (email: string, password: string) => {
        let supabase;
        try {
          supabase = getSupabaseClient();
        } catch (error) {
          throw new Error(error instanceof Error ? error.message : "Supabase auth is not configured.");
        }
        const emailRedirectTo = `${window.location.origin}/auth/callback`;
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo },
        });
        if (error) {
          throw error;
        }
      },
      requestPasswordReset: async (email: string) => {
        let supabase;
        try {
          supabase = getSupabaseClient();
        } catch (error) {
          throw new Error(error instanceof Error ? error.message : "Supabase auth is not configured.");
        }
        const redirectTo = `${window.location.origin}/auth/callback`;
        const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo });
        if (error) {
          throw error;
        }
      },
      updateEmail: async (email: string) => {
        let supabase;
        try {
          supabase = getSupabaseClient();
        } catch (error) {
          throw new Error(error instanceof Error ? error.message : "Supabase auth is not configured.");
        }
        const { data, error } = await supabase.auth.updateUser(
          { email },
          {
            emailRedirectTo: `${window.location.origin}/auth/callback`,
          },
        );
        if (error) {
          throw error;
        }
        return {
          currentEmail: data.user?.email ?? null,
          pendingEmail: (data.user as User & { new_email?: string | null })?.new_email ?? null,
        };
      },
      updatePassword: async (password: string) => {
        let supabase;
        try {
          supabase = getSupabaseClient();
        } catch (error) {
          throw new Error(error instanceof Error ? error.message : "Supabase auth is not configured.");
        }
        const { error } = await supabase.auth.updateUser({ password });
        if (error) {
          throw error;
        }
      },
      signOut: async () => {
        let supabase;
        try {
          supabase = getSupabaseClient();
        } catch {
          setSession(null);
          setUser(null);
          setApiAccessToken(null);
          return;
        }
        const { error } = await supabase.auth.signOut();
        if (error) {
          throw error;
        }
      },
    }),
    [user, session, isLoading, authError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
