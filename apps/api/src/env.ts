import { config } from "dotenv";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, "../../../.env") });

export function guestBaseUrl(): string {
  const publicBase = process.env.PUBLIC_BASE_URL?.replace(/\/$/, "");
  if (publicBase) return publicBase;
  return process.env.GUEST_WEB_URL?.replace(/\/$/, "") ?? "http://localhost:5173";
}
