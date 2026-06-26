import { Button, Card } from "@rekentafel/ui-core";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/v1";

const QR_FILES = ["T01.png", "T02.png", "T03.png", "T04.png", "rekentafel-qr-sheet.pdf"] as const;

export function QrDownloadPage({ onBack }: { onBack: () => void }) {
  return (
    <main className="staff-layout">
      <header className="staff-header">
        <Button variant="secondary" onClick={onBack}>
          ← Terug
        </Button>
        <h1>QR-codes printen</h1>
      </header>

      <Card title="Download voor print">
        <p className="muted">
          Print <strong>rekentafel-qr-sheet.pdf</strong> (A4, 4 tafels) of download losse PNGs.
          Run eerst <code>./scripts/rekentafel-poc.sh</code> op de Mac mini.
        </p>
        <ul className="qr-download-list">
          {QR_FILES.map((file) => (
            <li key={file}>
              <a
                href={`${API_BASE}/admin/qr-codes/${file}`}
                download={file}
                target="_blank"
                rel="noreferrer"
              >
                {file}
              </a>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="Tafels">
        <ul className="qr-table-list">
          <li>T01 — linkerboven</li>
          <li>T02 — rechterboven</li>
          <li>T03 — linkeronder</li>
          <li>T04 — rechtsonder</li>
        </ul>
        <p className="muted">Plak elke QR op de juiste tafel voor de demo.</p>
      </Card>
    </main>
  );
}
