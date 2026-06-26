import type { ReactNode } from "react";

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
  disabled,
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary";
  disabled?: boolean;
  type?: "button" | "submit" | "reset";
}) {
  return (
    <button
      type={type}
      className={`rt-btn rt-btn--${variant}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div className="rt-card">
      {title ? <h2 className="rt-card__title">{title}</h2> : null}
      {children}
    </div>
  );
}

export function QrDisplay({ url, label }: { url: string; label: string }) {
  const qrImageUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(url)}`;
  return (
    <div className="rt-qr">
      <img src={qrImageUrl} alt={`QR code for ${label}`} width={200} height={200} />
      <p className="rt-qr__label">{label}</p>
      <p className="rt-qr__url">{url}</p>
    </div>
  );
}
