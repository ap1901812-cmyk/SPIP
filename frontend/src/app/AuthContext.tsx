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
    authApi.logout();
    setUser(null);
  }, []);

  const loadCurrentUser = useCallback(async () => {
    try {
      const profile = await authApi.getCurrentUser();
      setUser(profile);
    } catch {
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    setUnauthorizedCallback(logout);
    const token = localStorage.getItem("spip_token");
    if (token) {
      loadCurrentUser();
    } else {
      setIsLoading(false);
    }
  }, [loadCurrentUser, logout]);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      await authApi.login(username, password);
      await loadCurrentUser();
    } finally {
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

