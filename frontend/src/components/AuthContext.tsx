"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

type AuthState = {
    token: string | null;
    username: string | null;
    isLoading: boolean;
    error: string | null;
    login: (username: string, password: string) => Promise<boolean>;
    logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

const TOKEN_KEY = "kanban_token";

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
    const [token, setToken] = useState<string | null>(null);
    const [username, setUsername] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const stored = sessionStorage.getItem(TOKEN_KEY);
        if (!stored) {
            setIsLoading(false);
            return;
        }

        fetch("/api/auth/me", {
            headers: { Authorization: `Bearer ${stored}` },
        })
            .then((res) => {
                if (!res.ok) throw new Error("Session expired");
                return res.json();
            })
            .then((data) => {
                setToken(stored);
                setUsername(data.username);
            })
            .catch(() => {
                sessionStorage.removeItem(TOKEN_KEY);
            })
            .finally(() => setIsLoading(false));
    }, []);

    const login = useCallback(async (user: string, pass: string) => {
        setError(null);
        try {
            const res = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: user, password: pass }),
            });
            if (!res.ok) {
                setError("Invalid username or password");
                return false;
            }
            const data = await res.json();
            sessionStorage.setItem(TOKEN_KEY, data.token);
            setToken(data.token);
            setUsername(data.username);
            return true;
        } catch {
            setError("Unable to connect to server");
            return false;
        }
    }, []);

    const logout = useCallback(async () => {
        if (token) {
            await fetch("/api/auth/logout", {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            }).catch(() => { });
        }
        sessionStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUsername(null);
    }, [token]);

    return (
        <AuthContext value={{ token, username, isLoading, error, login, logout }}>
            {children}
        </AuthContext>
    );
};

export const useAuth = () => {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within AuthProvider");
    return ctx;
};
