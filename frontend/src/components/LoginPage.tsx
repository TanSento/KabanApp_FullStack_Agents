"use client";

import { useState, type FormEvent } from "react";
import { useAuth } from "@/components/AuthContext";

export const LoginPage = () => {
    const { login, register, error } = useAuth();
    const [mode, setMode] = useState<"login" | "register">("login");
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [localError, setLocalError] = useState<string | null>(null);

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setLocalError(null);

        if (mode === "register" && password !== confirmPassword) {
            setLocalError("Passwords do not match");
            return;
        }

        setIsSubmitting(true);
        if (mode === "login") {
            await login(username, password);
        } else {
            await register(username, password);
        }
        setIsSubmitting(false);
    };

    const switchMode = (newMode: "login" | "register") => {
        setMode(newMode);
        setLocalError(null);
        setPassword("");
        setConfirmPassword("");
    };

    const displayError = localError || error;

    return (
        <div className="relative flex min-h-screen items-center justify-center overflow-hidden">
            <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
            <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

            <div className="relative w-full max-w-md rounded-[32px] border border-[var(--stroke)] bg-white/80 p-10 shadow-[var(--shadow)] backdrop-blur">
                <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                    {mode === "login" ? "Welcome back" : "Create account"}
                </p>
                <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
                    {mode === "login" ? "Sign in to Kanban Studio" : "Join Kanban Studio"}
                </h1>
                <p className="mt-3 text-sm leading-6 text-[var(--gray-text)]">
                    {mode === "login"
                        ? "Enter your credentials to access your board."
                        : "Choose a username and password to get started."}
                </p>

                <form onSubmit={handleSubmit} className="mt-8 space-y-5">
                    <div>
                        <label
                            htmlFor="login-username"
                            className="mb-2 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                        >
                            Username
                        </label>
                        <input
                            id="login-username"
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="w-full rounded-xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                            required
                            autoComplete="username"
                            minLength={mode === "register" ? 3 : undefined}
                        />
                    </div>

                    <div>
                        <label
                            htmlFor="login-password"
                            className="mb-2 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                        >
                            Password
                        </label>
                        <input
                            id="login-password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full rounded-xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                            required
                            autoComplete={mode === "login" ? "current-password" : "new-password"}
                            minLength={mode === "register" ? 6 : undefined}
                        />
                    </div>

                    {mode === "register" && (
                        <div>
                            <label
                                htmlFor="confirm-password"
                                className="mb-2 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                            >
                                Confirm Password
                            </label>
                            <input
                                id="confirm-password"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="w-full rounded-xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                                required
                                autoComplete="new-password"
                            />
                        </div>
                    )}

                    {displayError && (
                        <p className="text-sm font-medium text-red-600" role="alert">
                            {displayError}
                        </p>
                    )}

                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="w-full rounded-full bg-[var(--secondary-purple)] px-6 py-3 text-sm font-semibold uppercase tracking-wide text-white transition hover:brightness-110 disabled:opacity-60"
                    >
                        {isSubmitting
                            ? mode === "login" ? "Signing in..." : "Creating account..."
                            : mode === "login" ? "Sign in" : "Create account"}
                    </button>
                </form>

                <div className="mt-6 text-center">
                    {mode === "login" ? (
                        <p className="text-sm text-[var(--gray-text)]">
                            No account?{" "}
                            <button
                                type="button"
                                onClick={() => switchMode("register")}
                                className="font-semibold text-[var(--primary-blue)] hover:underline"
                                data-testid="switch-to-register"
                            >
                                Create one
                            </button>
                        </p>
                    ) : (
                        <p className="text-sm text-[var(--gray-text)]">
                            Already have an account?{" "}
                            <button
                                type="button"
                                onClick={() => switchMode("login")}
                                className="font-semibold text-[var(--primary-blue)] hover:underline"
                                data-testid="switch-to-login"
                            >
                                Sign in
                            </button>
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
};
