import { prisma } from "@rekentafel/db";

export type MenuPayload = {
  categories: {
    category_id: string;
    name: string;
    items: {
      item_id: string;
      name: string;
      description: string | null;
      price_inc_vat_cents: number;
      vat_rate_bps: number;
      allergens: string[];
    }[];
  }[];
};

export async function loadVenueMenu(venueId: string): Promise<MenuPayload> {
  const categories = await prisma.menuCategory.findMany({
    where: { venueId },
    orderBy: { sortOrder: "asc" },
    include: {
      items: {
        where: { isAvailable: true },
        orderBy: { sortOrder: "asc" },
      },
    },
  });

  return {
    categories: categories.map((category) => ({
      category_id: category.id,
      name: category.name,
      items: category.items.map((item) => ({
        item_id: item.id,
        name: item.name,
        description: item.description,
        price_inc_vat_cents: item.priceDisplayCents,
        vat_rate_bps: item.vatRateBps,
        allergens: Array.isArray(item.allergensJson)
          ? (item.allergensJson as string[])
          : [],
      })),
    })),
  };
}
