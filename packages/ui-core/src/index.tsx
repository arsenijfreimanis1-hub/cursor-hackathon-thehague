import type { ReactNode, CSSProperties } from "react";

export function formatEuro(cents: number): string {
  return new Intl.NumberFormat("nl-NL", {
    style: "currency",
    currency: "EUR",
  }).format(cents / 100);
}

export function Button({
  children,
  onClick,
  variant = "primary",
  size,
  disabled,
  type = "button",
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm";
  disabled?: boolean;
  type?: "button" | "submit" | "reset";
  className?: string;
}) {
  const classes = [
    "rt-btn",
    `rt-btn--${variant}`,
    size === "sm" ? "rt-btn--sm" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <button type={type} className={classes} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}

export function Card({
  title,
  subtitle,
  children,
  className,
  flat,
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  flat?: boolean;
}) {
  const classes = ["rt-card", flat ? "rt-card--flat" : "", className ?? ""].filter(Boolean).join(" ");
  return (
    <div className={classes}>
      {title ? <h2 className="rt-card__title">{title}</h2> : null}
      {subtitle ? <p className="rt-card__subtitle">{subtitle}</p> : null}
      {children}
    </div>
  );
}

export function Badge({
  children,
  variant = "muted",
  dot,
}: {
  children: ReactNode;
  variant?: "success" | "warning" | "muted";
  dot?: boolean;
}) {
  return (
    <span className={`rt-badge rt-badge--${variant}`}>
      {dot ? <span className="rt-badge__dot" /> : null}
      {children}
    </span>
  );
}

export function MoneyHero({
  label,
  amountCents,
  sub,
}: {
  label: string;
  amountCents: number;
  sub?: string;
}) {
  return (
    <div className="rt-money-hero">
      <p className="rt-money-hero__label">{label}</p>
      <p className="rt-money-hero__amount">{formatEuro(amountCents)}</p>
      {sub ? <p className="rt-money-hero__sub">{sub}</p> : null}
    </div>
  );
}

export function Chip({ name }: { name: string }) {
  const initial = name.trim().charAt(0).toUpperCase() || "?";
  return (
    <span className="rt-chip">
      <span className="rt-chip__avatar">{initial}</span>
      {name}
    </span>
  );
}

export function PinDisplay({ pin }: { pin: string }) {
  const digits = pin.padEnd(6, " ").split("").slice(0, 6);
  return (
    <div className="rt-pin" aria-label={`Pincode ${pin}`}>
      {digits.map((d, i) => (
        <span key={i} className="rt-pin__digit">
          {d.trim() || "·"}
        </span>
      ))}
    </div>
  );
}

export function ProgressBar({ percent }: { percent: number }) {
  const clamped = Math.min(100, Math.max(0, percent));
  return (
    <div className="rt-progress" role="progressbar" aria-valuenow={clamped}>
      <div className="rt-progress__fill" style={{ width: `${clamped}%` } as CSSProperties} />
    </div>
  );
}

export function PageShell({
  title,
  subtitle,
  children,
  footer,
  back,
  headerExtra,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
  back?: ReactNode;
  headerExtra?: ReactNode;
}) {
  return (
    <div className="rt-page">
      <header className="rt-page__header">
        {back}
        <div className="rt-page__header-row">
          <div>
            <h1>{title}</h1>
            {subtitle ? <p>{subtitle}</p> : null}
          </div>
          {headerExtra}
        </div>
      </header>
      <div className="rt-page__body">{children}</div>
      {footer ? <footer className="rt-page__footer">{footer}</footer> : null}
    </div>
  );
}

export function Spinner() {
  return <div className="rt-spinner" role="status" aria-label="Laden" />;
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="rt-field">
      <label>{label}</label>
      {children}
    </div>
  );
}

export function QrDisplay({ url, label }: { url: string; label: string }) {
  const qrImageUrl = `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(url)}&bgcolor=ffffff&color=2d6a4f`;
  return (
    <div className="rt-qr">
      <img src={qrImageUrl} alt={`QR code voor ${label}`} width={200} height={200} />
      <p className="rt-qr__label">Tafel {label}</p>
      <p className="rt-qr__url">{url}</p>
    </div>
  );
}

export function BillItem({
  name,
  priceCents,
  meta,
  action,
}: {
  name: string;
  priceCents: number;
  meta?: string;
  action?: ReactNode;
}) {
  return (
    <div className="rt-bill-item">
      <div>
        <p className="rt-bill-item__name">{name}</p>
        {meta ? <p className="rt-bill-item__meta">{meta}</p> : null}
        {action ? <div className="rt-bill-item__claim">{action}</div> : null}
      </div>
      <span className="rt-bill-item__price">{formatEuro(priceCents)}</span>
    </div>
  );
}
