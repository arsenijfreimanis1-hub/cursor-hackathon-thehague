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
const TABLE_CODES = ["T01", "T02", "T03", "T04"] as const;

function guestBaseUrl(): string {
  const publicBase = process.env.PUBLIC_BASE_URL?.replace(/\/$/, "");
  if (publicBase) return publicBase;
  return process.env.GUEST_WEB_URL?.replace(/\/$/, "") ?? "http://localhost:5173";
}

async function loadUrlsFromDb(): Promise<Map<string, string>> {
  const urls = new Map<string, string>();
  const base = guestBaseUrl();
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
  for (const code of TABLE_CODES) {
    if (!urls.has(code)) {
      urls.set(code, `${base}/t/${RESTAURANT_SLUG}/${code}`);
    }
  }
  return urls;
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

  // A4 PDF — 2×2 grid
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
