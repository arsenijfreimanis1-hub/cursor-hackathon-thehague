import type { MoneyCents } from "@rekentafel/shared-types";

/** MVP-lite: 1 point per euro of food (excl. tip). */
export const POINTS_PER_EURO_CENTS = 100;

export function accruePointsFromPayment(foodCents: MoneyCents): number {
  return Math.floor(foodCents / POINTS_PER_EURO_CENTS);
}

export type RewardsAccrual = {
  guestDeviceId: string;
  paymentSessionId: string;
  points: number;
};
