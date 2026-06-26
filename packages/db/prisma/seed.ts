/**
 * Dev seed: demo restaurant with tables and QR codes.
 * Run: pnpm --filter @rekentafel/db db:seed
 */
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

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

  const tableCodes = ["T01", "T02", "T03", "T04"];
  const guestWebUrl = process.env.GUEST_WEB_URL ?? "http://localhost:5173";

  for (const [index, tableCode] of tableCodes.entries()) {
    const table = await prisma.table.upsert({
      where: { venueId_tableCode: { venueId: venue.id, tableCode } },
      update: {},
      create: {
        venueId: venue.id,
        tableCode,
        seats: 4,
        sortOrder: index,
      },
    });

    const publicSlug = `demo-${tableCode.toLowerCase()}`;
    const qrPayloadUrl = `${guestWebUrl}/t/${restaurant.slug}/${tableCode}`;

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
