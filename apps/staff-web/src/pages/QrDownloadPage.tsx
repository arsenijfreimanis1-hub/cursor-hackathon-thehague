import { Button, Card } from "@rekentafel/ui-core";
import { LanguageSwitcher, useT } from "@rekentafel/i18n";
import { API_BASE } from "../config";

const QR_FILES = ["rekentafel-qr-sheet.pdf", "T01.png", "T02.png", "T03.png", "T04.png"] as const;

export function QrDownloadPage({ onBack }: { onBack: () => void }) {
  const t = useT();

  return (
    <main className="staff-layout">
      <div className="detail-back">
        <Button variant="ghost" size="sm" onClick={onBack}>
          {t("staff.table.back")}
        </Button>
        <LanguageSwitcher />
      </div>

      <header className="detail-header">
        <h1>{t("staff.qr.title")}</h1>
        <p>{t("staff.qr.subtitle")}</p>
      </header>

      <div className="detail-grid">
        <Card title={t("staff.qr.download")} subtitle={t("staff.qr.downloadHint")}>
          <ul className="qr-download-list">
            {QR_FILES.map((file) => (
              <li key={file}>
                <a
                  href={`${API_BASE}/admin/qr-codes/${file}`}
                  download={file}
                  target="_blank"
                  rel="noreferrer"
                >
                  {file === "rekentafel-qr-sheet.pdf" ? t("staff.qr.sheet") : file.replace(".png", "")}
                </a>
              </li>
            ))}
          </ul>
        </Card>

        <Card title={t("staff.qr.placement")} flat>
          <ul className="qr-table-list">
            <li>{t("staff.qr.t01")}</li>
            <li>{t("staff.qr.t02")}</li>
            <li>{t("staff.qr.t03")}</li>
            <li>{t("staff.qr.t04")}</li>
          </ul>
        </Card>
      </div>
    </main>
  );
}
