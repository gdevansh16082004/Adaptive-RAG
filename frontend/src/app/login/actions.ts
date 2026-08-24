"use server";

import { AuthError } from "next-auth";
import bcrypt from "bcryptjs";

import { signIn } from "@/auth";
import { createUser } from "@/lib/mongo";

export type AuthFormState = {
  error?: string;
};

const USERNAME_PATTERN = /^[a-zA-Z0-9_.-]{3,32}$/;

export async function loginAction(
  _prev: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  try {
    await signIn("credentials", {
      username: formData.get("username"),
      password: formData.get("password"),
      redirectTo: "/chat",
    });
  } catch (error) {
    if (error instanceof AuthError) {
      return { error: "Invalid username or password." };
    }
    throw error; // NEXT_REDIRECT and friends must bubble up
  }
  return {};
}

export async function registerAction(
  _prev: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const username = String(formData.get("username") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  if (!USERNAME_PATTERN.test(username)) {
    return {
      error:
        "Username must be 3-32 characters (letters, numbers, dot, dash, underscore).",
    };
  }
  if (password.length < 6) {
    return { error: "Password must be at least 6 characters." };
  }

  try {
    await createUser(username, await bcrypt.hash(password, 10));
  } catch (error) {
    return {
      error:
        error instanceof Error ? error.message : "Registration failed. Try again.",
    };
  }

  try {
    await signIn("credentials", {
      username,
      password,
      redirectTo: "/chat",
    });
  } catch (error) {
    if (error instanceof AuthError) {
      return { error: "Account created — please sign in." };
    }
    throw error;
  }
  return {};
}
