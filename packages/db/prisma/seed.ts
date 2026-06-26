/**
 * Dev seed: demo restaurant with tables and QR codes.
 * Run: pnpm --filter @rekentafel/db db:seed
 */
import { config } from "dotenv";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { PrismaClient } from "@prisma/client";

const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, "../../../.env") });

const prisma = new PrismaClient();

function guestBaseUrl(): string {
  const publicBase = process.env.PUBLIC_BASE_URL?.replace(/\/$/, "");
  if (publicBase) return publicBase;
  return process.env.GUEST_WEB_URL?.replace(/\/$/, "") ?? "http://localhost:5173";
}

async function main() {
  const restaurant = await prisma.restaurant.upsert({
    where: { slug: "demo-bistro" },
    update: {},
    create: {
      slug: "demo-bistro",
      legalName: "Demo Bistro B.V.",
      tradeName: "Demo Bistro",
      status: "ACTIVE",
      paymentsEnabled: true,
    },
  });

  const venue = await prisma.venue.upsert({
    where: { id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" },
    update: {},
    create: {
      id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      restaurantId: restaurant.id,
      name: "Hoofdzaal",
      timezone: "Europe/Amsterdam",
    },
  });

  const tableLayout: { code: string; posX: number; posY: number }[] = [
    { code: "T01", posX: 25, posY: 25 },
    { code: "T02", posX: 75, posY: 25 },
    { code: "T03", posX: 25, posY: 75 },
    { code: "T04", posX: 75, posY: 75 },
  ];

  const guestWebUrl = guestBaseUrl();

  for (const [index, layout] of tableLayout.entries()) {
    const table = await prisma.table.upsert({
      where: { venueId_tableCode: { venueId: venue.id, tableCode: layout.code } },
      update: { posX: layout.posX, posY: layout.posY, seats: 4 },
      create: {
        venueId: venue.id,
        tableCode: layout.code,
        seats: 4,
        posX: layout.posX,
        posY: layout.posY,
        sortOrder: index,
      },
    });

    const publicSlug = `demo-${layout.code.toLowerCase()}`;
    const qrPayloadUrl = `${guestWebUrl}/t/${restaurant.slug}/${layout.code}`;

    await prisma.tableQrCode.upsert({
      where: { tableId: table.id },
      update: { qrPayloadUrl },
      create: {
        tableId: table.id,
        publicSlug,
        qrPayloadUrl,
      },
    });
  }

  console.log(`Seeded restaurant ${restaurant.slug}, venue ${venue.id}`);
  console.log(`QR base URL: ${guestWebUrl}`);
  console.log(`Set DEV_VENUE_ID=${venue.id} in .env for staff API`);

  const user = await prisma.user.upsert({
    where: { email: "waiter@demo.rekentafel.nl" },
    update: {},
    create: {
      email: "waiter@demo.rekentafel.nl",
      displayName: "Demo Waiter",
      status: "ACTIVE",
    },
  });

  const staff = await prisma.staffMember.upsert({
    where: { id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb" },
    update: {},
    create: {
      id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      restaurantId: restaurant.id,
      venueId: venue.id,
      userId: user.id,
      role: "WAITER",
      isActive: true,
    },
  });

  console.log(`Set DEV_STAFF_ID=${staff.id} in .env for payment activation`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
