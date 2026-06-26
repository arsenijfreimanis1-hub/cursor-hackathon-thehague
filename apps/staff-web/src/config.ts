/** Baked in at build time — run scripts/prepare-waiter-ios.sh on MacBook before Xcode. */
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/v1";
export const LAN_HOST = import.meta.env.VITE_LAN_HOST ?? "";
