/**
 * Generate print-ready QR codes for tables T01–T04.
 * Output: data/qr-codes/T01.png … T04.png + rekentafel-qr-sheet.pdf
 */
import { config } from "dotenv";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdir, writeFile } from "node:fs/promises";
import QRCode from "qrcode";
import { PDFDocument, rgb, StandardFonts } from "pdf-lib";
import { PrismaClient } from "@prisma/client";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
config({ path: resolve(ROOT, ".env") });

const OUT_DIR = resolve(ROOT, "data/qr-codes");
const RESTAURANT_SLUG = "demo-bistro";
const TABLE_CODES = (process.env.TABLE_CODES ?? "T01,T02,T03,T04")
  .split(",")
  .map((c) => c.trim()) as readonly string[];

function guestBaseUrl(): string {
  const lan = process.env.VITE_LAN_HOST?.trim();
  if (lan) return `http://${lan}:5173`;
  const publicBase = process.env.PUBLIC_BASE_URL?.replace(/\/$/, "");
  if (publicBase) return publicBase;
  return process.env.GUEST_WEB_URL?.replace(/\/$/, "") ?? "http://localhost:5173";
}

async function loadUrlsFromDb(): Promise<Map<string, string>> {
  const urls = new Map<string, string>();
  const base = guestBaseUrl();
  const preferConstructed =
    Boolean(process.env.VITE_LAN_HOST?.trim()) || Boolean(process.env.PUBLIC_BASE_URL?.trim());

  if (!preferConstructed) {
    try {
      const prisma = new PrismaClient();
      const restaurant = await prisma.restaurant.findUnique({ where: { slug: RESTAURANT_SLUG } });
      if (restaurant) {
        const qrCodes = await prisma.tableQrCode.findMany({
          where: { table: { venue: { restaurantId: restaurant.id } } },
          include: { table: true },
        });
        for (const qr of qrCodes) {
          urls.set(qr.table.tableCode, qr.qrPayloadUrl);
        }
      }
      await prisma.$disconnect();
    } catch {
      // Fall back to constructed URLs if DB unavailable
    }
  }

  for (const code of TABLE_CODES) {
    if (preferConstructed || !urls.has(code)) {
      urls.set(code, `${base}/t/${RESTAURANT_SLUG}/${code}`);
    }
  }
  return urls;
}

async function writeDemoScreen(pngBuffers: { code: string; url: string; png: Buffer }[]) {
  const cards = pngBuffers
    .map(
      ({ code, url, png }) => `
    <section class="card">
      <h2>${code}</h2>
      <img src="data:image/png;base64,${png.toString("base64")}" alt="QR ${code}" width="280" height="280" />
      <p class="url">${url}</p>
      <a class="link" href="${url}">Open in browser →</a>
    </section>`,
    )
    .join("\n");

  const html = `<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Rekentafel — Demo QR</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0; min-height: 100dvh;
      font-family: system-ui, sans-serif;
      background: #0c0a09; color: #fafaf9;
      display: flex; flex-direction: column; align-items: center;
      padding: 1.5rem;
    }
    h1 { margin: 0 0 0.25rem; font-size: 1.5rem; }
    .sub { color: #a8a29e; margin: 0 0 1.5rem; text-align: center; }
    .grid {
      display: grid; gap: 1.25rem;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      max-width: 900px; width: 100%;
    }
    .card {
      background: #1c1917; border-radius: 16px;
      padding: 1.25rem; text-align: center;
      border: 1px solid rgba(255,255,255,0.08);
    }
    .card h2 { margin: 0 0 1rem; font-size: 1.75rem; color: #f59e0b; }
    .card img { border-radius: 12px; background: #fff; padding: 8px; }
    .url { font-size: 0.7rem; color: #78716c; word-break: break-all; margin: 0.75rem 0; }
    .link {
      display: inline-block; margin-top: 0.5rem;
      color: #34d399; font-weight: 600; text-decoration: none;
    }
  </style>
</head>
<body>
  <h1>Rekentafel Demo QR</h1>
  <p class="sub">Wi‑Fi: Titaan Members · Scan with camera or tap link</p>
  <div class="grid">${cards}</div>
</body>
</html>`;

  const screenPath = resolve(OUT_DIR, "demo-screen.html");
  await writeFile(screenPath, html);
  const publicPath = resolve(ROOT, "apps/guest-web/public/qr-demo.html");
  await mkdir(resolve(publicPath, ".."), { recursive: true });
  await writeFile(publicPath, html);
  console.log(`  demo-screen.html + guest-web /qr-demo.html`);
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true });
  const urls = await loadUrlsFromDb();

  const pngBuffers: { code: string; url: string; png: Buffer }[] = [];

  for (const code of TABLE_CODES) {
    const url = urls.get(code)!;
    const png = await QRCode.toBuffer(url, {
      type: "png",
      width: 512,
      margin: 2,
      errorCorrectionLevel: "H",
    });
    const pngPath = resolve(OUT_DIR, `${code}.png`);
    await writeFile(pngPath, png);
    pngBuffers.push({ code, url, png });
    console.log(`  ${code}.png → ${url}`);
  }

  await writeDemoScreen(pngBuffers);

  if (TABLE_CODES.length < 4) {
    console.log(`\nQR files saved to: ${OUT_DIR}`);
    return;
  }

  // A4 PDF — 2×2 grid (print sheet, all 4 tables)
  const pdf = await PDFDocument.create();
  const font = await pdf.embedFont(StandardFonts.Helvetica);
  const fontBold = await pdf.embedFont(StandardFonts.HelveticaBold);
  const page = pdf.addPage([595.28, 841.89]); // A4
  const w = page.getWidth();
  const h = page.getHeight();
  const cellW = w / 2;
  const cellH = h / 2;
  const qrSize = 180;

  const positions = [
    { code: "T01", col: 0, row: 0 },
    { code: "T02", col: 1, row: 0 },
    { code: "T03", col: 0, row: 1 },
    { code: "T04", col: 1, row: 1 },
  ];

  for (const { code, col, row } of positions) {
    const item = pngBuffers.find((p) => p.code === code)!;
    const img = await pdf.embedPng(item.png);
    const x = col * cellW + (cellW - qrSize) / 2;
    const y = h - (row + 1) * cellH + (cellH - qrSize) / 2 + 20;
    page.drawImage(img, { x, y, width: qrSize, height: qrSize });
    page.drawText(`Tafel ${code}`, {
      x: col * cellW + cellW / 2 - 30,
      y: y + qrSize + 12,
      size: 16,
      font: fontBold,
      color: rgb(0.1, 0.1, 0.1),
    });
    page.drawText("Scan om rekening te splitsen", {
      x: col * cellW + 20,
      y: y - 18,
      size: 9,
      font,
      color: rgb(0.4, 0.4, 0.4),
    });
  }

  page.drawText("Rekentafel — Demo Bistro", {
    x: w / 2 - 80,
    y: h - 30,
    size: 12,
    font: fontBold,
    color: rgb(0.2, 0.2, 0.2),
  });

  const pdfBytes = await pdf.save();
  const pdfPath = resolve(OUT_DIR, "rekentafel-qr-sheet.pdf");
  await writeFile(pdfPath, pdfBytes);
  console.log(`  rekentafel-qr-sheet.pdf (print this)`);
  console.log(`\nQR files saved to: ${OUT_DIR}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
