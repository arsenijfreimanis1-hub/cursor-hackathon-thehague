/** Resolve API base — LAN phones use the same host as the guest web app. */
export function resolveApiBase(override?: string): string {
  if (override) return override;
  const fromEnv = import.meta.env.VITE_API_BASE_URL;
  if (fromEnv) return fromEnv.replace(/\/$/, "");

  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host !== "localhost" && host !== "127.0.0.1") {
      return `http://${host}:3000/v1`;
    }
  }

  return "http://localhost:3000/v1";
}

export const API_BASE = resolveApiBase();
export const LAN_HOST = import.meta.env.VITE_LAN_HOST ?? "";
