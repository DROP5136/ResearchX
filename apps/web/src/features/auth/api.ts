import { apiFetch, setToken } from "@/api/client";
import type { User } from "@/types/api";

export async function register(input: { name: string; email: string; password: string }) {
  const data = await apiFetch<{ token: string; user: User }>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
  setToken(data.token);
  return data;
}

export async function login(input: { email: string; password: string }) {
  const data = await apiFetch<{ token: string; user: User }>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
  setToken(data.token);
  return data;
}

export async function me() {
  return apiFetch<{ user: User }>("/api/v1/auth/me");
}

export function logout() {
  setToken(null);
}
