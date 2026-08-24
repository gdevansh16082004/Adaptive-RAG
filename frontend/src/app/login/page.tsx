"use client";

import { useActionState, useState } from "react";

import { loginAction, registerAction, type AuthFormState } from "./actions";

const initialState: AuthFormState = {};

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [loginState, submitLogin, loginPending] = useActionState(
    loginAction,
    initialState,
  );
  const [registerState, submitRegister, registerPending] = useActionState(
    registerAction,
    initialState,
  );

  const state = mode === "login" ? loginState : registerState;
  const pending = mode === "login" ? loginPending : registerPending;

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-center text-2xl font-semibold text-zinc-50">
          Adaptive RAG
        </h1>
        <p className="mb-8 text-center text-sm text-zinc-400">
          Agentic chat over your own documents
        </p>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-6 shadow-xl">
          <div className="mb-6 grid grid-cols-2 rounded-lg bg-zinc-800 p-1 text-sm font-medium">
            {(["login", "register"] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setMode(value)}
                className={`rounded-md px-3 py-2 transition ${
                  mode === value
                    ? "bg-emerald-600 text-white"
                    : "text-zinc-300 hover:text-white"
                }`}
              >
                {value === "login" ? "Sign in" : "Create account"}
              </button>
            ))}
          </div>

          <form action={mode === "login" ? submitLogin : submitRegister}>
            <label
              htmlFor="username"
              className="mb-1 block text-xs font-medium text-zinc-400"
            >
              Username
            </label>
            <input
              id="username"
              name="username"
              autoComplete="username"
              required
              minLength={3}
              maxLength={32}
              className="mb-4 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none placeholder:text-zinc-500 focus:border-emerald-500"
              placeholder="alice"
            />

            <label
              htmlFor="password"
              className="mb-1 block text-xs font-medium text-zinc-400"
            >
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={6}
              className="mb-4 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none placeholder:text-zinc-500 focus:border-emerald-500"
              placeholder="••••••••"
            />

            {state?.error && (
              <p
                role="alert"
                className="mb-4 rounded-lg border border-red-900/60 bg-red-950/40 px-3 py-2 text-xs text-red-300"
              >
                {state.error}
              </p>
            )}

            <button
              type="submit"
              disabled={pending}
              className="w-full rounded-lg bg-emerald-600 px-3 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {pending
                ? "Working…"
                : mode === "login"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}
