import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { en, nl, type Locale, type Messages } from "./messages.js";

const STORAGE_KEY = "rekentafel_locale";

function getByPath(obj: Messages, path: string): string {
  const parts = path.split(".");
  let cur: unknown = obj;
  for (const part of parts) {
    if (cur == null || typeof cur !== "object") return path;
    cur = (cur as Record<string, unknown>)[part];
  }
  return typeof cur === "string" ? cur : path;
}

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, vars?: Record<string, string>) => string;
  messages: Messages;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function detectLocale(): Locale {
  if (typeof window === "undefined") return "nl";
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "en" || stored === "nl") return stored;
  const lang = navigator.language.toLowerCase();
  return lang.startsWith("en") ? "en" : "nl";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(detectLocale);

  const messages = locale === "en" ? en : nl;

  const setLocale = useCallback((next: Locale) => {
    localStorage.setItem(STORAGE_KEY, next);
    setLocaleState(next);
    document.documentElement.lang = next;
  }, []);

  const t = useCallback(
    (key: string, vars?: Record<string, string>) => {
      let text = getByPath(messages, key);
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          text = text.replace(`{${k}}`, v);
        }
      }
      return text;
    },
    [messages],
  );

  const value = useMemo(
    () => ({ locale, setLocale, t, messages }),
    [locale, setLocale, t, messages],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

export function useT() {
  return useI18n().t;
}

export function LanguageSwitcher({ className }: { className?: string }) {
  const { locale, setLocale } = useI18n();
  return (
    <div className={className ?? "rt-lang-switch"} role="group" aria-label="Language">
      {(["nl", "en"] as const).map((code) => (
        <button
          key={code}
          type="button"
          className={`rt-lang-switch__btn${locale === code ? " rt-lang-switch__btn--active" : ""}`}
          onClick={() => setLocale(code)}
          aria-pressed={locale === code}
        >
          {code.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

export { type Locale, type Messages } from "./messages.js";

export function NetworkBanner({
  port,
  variant,
  lanHost,
}: {
  port: 5173 | 5174;
  variant: "guest" | "staff";
  lanHost?: string;
}) {
  const { t } = useI18n();
  if (!lanHost || typeof window === "undefined") return null;
  if (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
    return null;
  }
  const url = `http://${lanHost}:${port}`;
  const label = variant === "guest" ? t("network.body") : t("network.staffBody");
  return (
    <div className="rt-network-banner">
      <strong>{t("network.title")}</strong>
      <p>{label}</p>
      <code className="rt-network-banner__url">{url}</code>
      <p className="rt-network-banner__wifi">Wi‑Fi: Titaan Members</p>
    </div>
  );
}
