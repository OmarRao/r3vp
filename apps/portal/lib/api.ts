import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  withCredentials: true,
});

// Attach Auth0 access token from the session on every request
api.interceptors.request.use(async (config) => {
  if (typeof window !== "undefined") {
    try {
      const resp = await fetch("/api/auth/token");
      if (resp.ok) {
        const { accessToken } = await resp.json();
        if (accessToken) {
          config.headers.Authorization = `Bearer ${accessToken}`;
        }
      }
    } catch {
      // unauthenticated — middleware will redirect
    }
  }
  return config;
});
