/**
 * Registry-aligned TypeScript enums for Rekentafel MVP.
 * Canonical names match entity-dictionary.md and openapi.yaml.
 */

export const TableSessionState = {
  DORMANT: "DORMANT",
  SEATED: "SEATED",
  ORDERED: "ORDERED",
  READY_TO_PAY: "READY_TO_PAY",
  PAID: "PAID",
  CLOSED: "CLOSED",
} as const;
export type TableSessionState =
  (typeof TableSessionState)[keyof typeof TableSessionState];

export const TableBillSettlementState = {
  BILL_DRAFT: "BILL_DRAFT",
  ALLOCATION_OPEN: "ALLOCATION_OPEN",
  ALLOCATION_FROZEN: "ALLOCATION_FROZEN",
  CHECKOUT_IN_PROGRESS: "CHECKOUT_IN_PROGRESS",
  PARTIALLY_PAID: "PARTIALLY_PAID",
  FULLY_PAID: "FULLY_PAID",
  CLOSED: "CLOSED",
  VOID: "VOID",
} as const;
export type TableBillSettlementState =
  (typeof TableBillSettlementState)[keyof typeof TableBillSettlementState];

export const SplitMode = {
  ITEM: "ITEM",
  EQUAL: "EQUAL",
  CUSTOM: "CUSTOM",
  SHARED: "SHARED",
} as const;
export type SplitMode = (typeof SplitMode)[keyof typeof SplitMode];

export const ParticipantState = {
  JOINED: "JOINED",
  ALLOCATING: "ALLOCATING",
  CHECKOUT_LOCKED: "CHECKOUT_LOCKED",
  PAYMENT_PENDING: "PAYMENT_PENDING",
  PAID: "PAID",
  PAYMENT_FAILED: "PAYMENT_FAILED",
  RELEASED: "RELEASED",
  OVERRIDDEN: "OVERRIDDEN",
} as const;
export type ParticipantState =
  (typeof ParticipantState)[keyof typeof ParticipantState];

export const PaymentStatus = {
  CREATING: "CREATING",
  MOLLIE_OPEN: "MOLLIE_OPEN",
  PAID: "PAID",
  FAILED: "FAILED",
  CANCELED: "CANCELED",
  EXPIRED: "EXPIRED",
  PARTIALLY_REFUNDED: "PARTIALLY_REFUNDED",
  REFUNDED: "REFUNDED",
  CHARGEBACK: "CHARGEBACK",
} as const;
export type PaymentStatus =
  (typeof PaymentStatus)[keyof typeof PaymentStatus];

export const PaymentSessionState = {
  OPEN: "OPEN",
  PARTIALLY_PAID: "PARTIALLY_PAID",
  FULLY_PAID: "FULLY_PAID",
  CLOSED: "CLOSED",
  DISPUTED: "DISPUTED",
} as const;
export type PaymentSessionState =
  (typeof PaymentSessionState)[keyof typeof PaymentSessionState];

export const BillLineKind = {
  MENU_ITEM: "MENU_ITEM",
  SERVICE_CHARGE: "SERVICE_CHARGE",
  DISCOUNT: "DISCOUNT",
  ROUNDING_ADJ: "ROUNDING_ADJ",
  MANUAL_MISC: "MANUAL_MISC",
} as const;
export type BillLineKind = (typeof BillLineKind)[keyof typeof BillLineKind];

export const AllocationState = {
  DRAFT: "DRAFT",
  COMMITTED: "COMMITTED",
  LOCKED_FOR_CHECKOUT: "LOCKED_FOR_CHECKOUT",
  RELEASED: "RELEASED",
  INVALIDATED: "INVALIDATED",
} as const;
export type AllocationState =
  (typeof AllocationState)[keyof typeof AllocationState];

export const RestaurantStatus = {
  DRAFT: "DRAFT",
  ONBOARDING: "ONBOARDING",
  ACTIVE: "ACTIVE",
  SUSPENDED: "SUSPENDED",
  CHURNED: "CHURNED",
} as const;
export type RestaurantStatus =
  (typeof RestaurantStatus)[keyof typeof RestaurantStatus];

export const StaffRole = {
  WAITER: "WAITER",
  MANAGER: "MANAGER",
  ADMIN: "ADMIN",
  PLATFORM_OPS: "PLATFORM_OPS",
} as const;
export type StaffRole = (typeof StaffRole)[keyof typeof StaffRole];

export const ServiceSignalType = {
  READY_TO_ORDER: "READY_TO_ORDER",
  ASSISTANCE: "ASSISTANCE",
} as const;
export type ServiceSignalType =
  (typeof ServiceSignalType)[keyof typeof ServiceSignalType];

export const ServiceSignalStatus = {
  OPEN: "OPEN",
  ACKNOWLEDGED: "ACKNOWLEDGED",
  EXPIRED: "EXPIRED",
} as const;
export type ServiceSignalStatus =
  (typeof ServiceSignalStatus)[keyof typeof ServiceSignalStatus];

export const TokenState = {
  ISSUED: "ISSUED",
  EXPIRED: "EXPIRED",
  REVOKED: "REVOKED",
} as const;
export type TokenState = (typeof TokenState)[keyof typeof TokenState];

export const CheckoutIntentState = {
  ACTIVE: "ACTIVE",
  CONSUMED: "CONSUMED",
  EXPIRED: "EXPIRED",
  CANCELLED: "CANCELLED",
} as const;
export type CheckoutIntentState =
  (typeof CheckoutIntentState)[keyof typeof CheckoutIntentState];

export const PaymentIntentStatus = {
  CREATING: "CREATING",
  MOLLIE_OPEN: "MOLLIE_OPEN",
  PAID: "PAID",
  FAILED: "FAILED",
  CANCELED: "CANCELED",
  EXPIRED: "EXPIRED",
  FAILED_CREATE: "FAILED_CREATE",
  PARTIALLY_REFUNDED: "PARTIALLY_REFUNDED",
  REFUNDED: "REFUNDED",
  CHARGEBACK: "CHARGEBACK",
} as const;
export type PaymentIntentStatus =
  (typeof PaymentIntentStatus)[keyof typeof PaymentIntentStatus];

export const SettlementStatus = {
  PENDING: "PENDING",
  AVAILABLE: "AVAILABLE",
  PAID_OUT: "PAID_OUT",
} as const;
export type SettlementStatus =
  (typeof SettlementStatus)[keyof typeof SettlementStatus];

export const WebhookSource = {
  MOLLIE: "MOLLIE",
  CRYPTO: "CRYPTO",
} as const;
export type WebhookSource = (typeof WebhookSource)[keyof typeof WebhookSource];

export const AuditActorType = {
  GUEST: "GUEST",
  STAFF: "STAFF",
  SYSTEM: "SYSTEM",
  MOLLIE_WEBHOOK: "MOLLIE_WEBHOOK",
} as const;
export type AuditActorType =
  (typeof AuditActorType)[keyof typeof AuditActorType];

/** Registry IDs — use exact names across slices. */
export type RegistryIds = {
  dining_session_id: string;
  payment_session_id: string;
  participant_id: string;
  bill_version: number;
  allocatable_unit_id: string;
  allocation_id: string;
  checkout_intent_id: string;
  payment_intent_id: string;
  guest_device_id: string;
  public_slug: string;
};

export type MoneyCents = number;
