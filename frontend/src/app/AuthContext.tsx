import { createContext, useCallback, useEffect, useState } from "react";

import { setUnauthorizedCallback } from "../api/client";
import { authApi } from "../api/services";
import type { UserProfile } from "../api/types";

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  reloadUser: () => Promise<void>;
  hasRole: (allowedRoles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    console.log("[AuthContext] logout called");
    authApi.logout();
    setUser(null);
  }, []);

  const loadCurrentUser = useCallback(async () => {
    console.log("[AuthContext] loadCurrentUser starting...");
    try {
      const profile = await authApi.getCurrentUser();
      console.log("[AuthContext] loadCurrentUser success, profile:", profile);
      setUser(profile);
    } catch (err) {
      console.error("[AuthContext] loadCurrentUser error:", err);
      logout();
    } finally {
      console.log("[AuthContext] loadCurrentUser finally, setting isLoading to false");
      setIsLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    console.log("[AuthContext] useEffect on mount, checking token...");
    setUnauthorizedCallback(logout);
    const token = localStorage.getItem("spip_token");
    if (token) {
      console.log("[AuthContext] Token found, calling loadCurrentUser");
      loadCurrentUser();
    } else {
      console.log("[AuthContext] No token found, setting isLoading to false");
      setIsLoading(false);
    }
  }, [loadCurrentUser, logout]);

  const login = async (username: string, password: string) => {
    console.log("[AuthContext] login starting, setting isLoading to true...");
    setIsLoading(true);
    try {
      await authApi.login(username, password);
      console.log("[AuthContext] login API success, awaiting loadCurrentUser...");
      await loadCurrentUser();
      console.log("[AuthContext] loadCurrentUser finished during login");
    } finally {
      console.log("[AuthContext] login finally, setting isLoading to false");
      setIsLoading(false);
    }
  };

  const reloadUser = async () => {
    await loadCurrentUser();
  };

  const hasRole = useCallback(
    (allowedRoles: string[]): boolean => {
      if (!user || !user.roles) return false;
      return user.roles.some((r) => {
        if (allowedRoles.includes(r)) return true;
        if (r === "Manager/Approver" && allowedRoles.includes("Manager")) return true;
        if (r === "Manager" && allowedRoles.includes("Manager/Approver")) return true;
        return false;
      });
    },
    [user]
  );

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, reloadUser, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export { AuthContext };

