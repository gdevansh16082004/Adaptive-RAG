"use client";

import { signOut } from "next-auth/react";

export default function SignOutButton({ username }: { username: string }) {
  return (
    <button
      type="button"
      onClick={() => void signOut({ callbackUrl: "/login" })}
      className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-zinc-500 hover:text-white"
    >
      Sign out {username}
    </button>
  );
}
