-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateEnum
CREATE TYPE "RestaurantStatus" AS ENUM ('DRAFT', 'ONBOARDING', 'ACTIVE', 'SUSPENDED', 'CHURNED');

-- CreateEnum
CREATE TYPE "UserStatus" AS ENUM ('ACTIVE', 'SUSPENDED', 'DELETED');

-- CreateEnum
CREATE TYPE "StaffRole" AS ENUM ('WAITER', 'MANAGER', 'ADMIN', 'PLATFORM_OPS');

-- CreateEnum
CREATE TYPE "DiningSessionState" AS ENUM ('EMPTY', 'SEATED', 'PAYMENT_ACTIVE', 'CLOSED');

-- CreateEnum
CREATE TYPE "CloseReasonCode" AS ENUM ('NORMAL', 'FORCE_CASH', 'WALKOUT', 'CANCEL');

-- CreateEnum
CREATE TYPE "PaymentSessionState" AS ENUM ('OPEN', 'PARTIALLY_PAID', 'FULLY_PAID', 'CLOSED', 'DISPUTED');

-- CreateEnum
CREATE TYPE "TokenState" AS ENUM ('ISSUED', 'EXPIRED', 'REVOKED');

-- CreateEnum
CREATE TYPE "ParticipantState" AS ENUM ('JOINED', 'ALLOCATING', 'CHECKOUT_LOCKED', 'PAYMENT_PENDING', 'PAID', 'PAYMENT_FAILED', 'RELEASED', 'OVERRIDDEN');

-- CreateEnum
CREATE TYPE "BillSettlementState" AS ENUM ('BILL_DRAFT', 'ALLOCATION_OPEN', 'ALLOCATION_FROZEN', 'CHECKOUT_IN_PROGRESS', 'PARTIALLY_PAID', 'FULLY_PAID', 'CLOSED', 'VOID');

-- CreateEnum
CREATE TYPE "BillLineKind" AS ENUM ('MENU_ITEM', 'SERVICE_CHARGE', 'DISCOUNT', 'ROUNDING_ADJ', 'MANUAL_MISC');

-- CreateEnum
CREATE TYPE "SplitMode" AS ENUM ('ITEM', 'EQUAL', 'CUSTOM', 'SHARED');

-- CreateEnum
CREATE TYPE "AllocationState" AS ENUM ('DRAFT', 'COMMITTED', 'LOCKED_FOR_CHECKOUT', 'RELEASED', 'INVALIDATED');

-- CreateEnum
CREATE TYPE "PledgeState" AS ENUM ('ACTIVE', 'LOCKED', 'SETTLED', 'CANCELLED');

-- CreateEnum
CREATE TYPE "CheckoutIntentState" AS ENUM ('ACTIVE', 'CONSUMED', 'EXPIRED', 'CANCELLED');

-- CreateEnum
CREATE TYPE "PaymentIntentStatus" AS ENUM ('CREATING', 'MOLLIE_OPEN', 'PAID', 'FAILED', 'CANCELED', 'EXPIRED', 'FAILED_CREATE', 'PARTIALLY_REFUNDED', 'REFUNDED', 'CHARGEBACK');

-- CreateEnum
CREATE TYPE "SettlementStatus" AS ENUM ('PENDING', 'AVAILABLE', 'PAID_OUT');

-- CreateEnum
CREATE TYPE "TipDestination" AS ENUM ('PASS_THROUGH', 'VENUE_POOL');

-- CreateEnum
CREATE TYPE "RefundStatus" AS ENUM ('PENDING', 'COMPLETED', 'FAILED');

-- CreateEnum
CREATE TYPE "ServiceSignalType" AS ENUM ('READY_TO_ORDER', 'ASSISTANCE');

-- CreateEnum
CREATE TYPE "ServiceSignalStatus" AS ENUM ('OPEN', 'ACKNOWLEDGED', 'EXPIRED');

-- CreateEnum
CREATE TYPE "OrderSource" AS ENUM ('MANUAL', 'POS_IMPORT', 'CSV');

-- CreateEnum
CREATE TYPE "OrderStatus" AS ENUM ('OPEN', 'CLOSED', 'VOID');

-- CreateEnum
CREATE TYPE "RewardsAccountStatus" AS ENUM ('ACTIVE', 'FROZEN', 'CLOSED');

-- CreateEnum
CREATE TYPE "RewardsEntryType" AS ENUM ('ACCRUAL', 'REVERSAL', 'REDEMPTION', 'ADJUSTMENT');

-- CreateEnum
CREATE TYPE "RedemptionStatus" AS ENUM ('REQUESTED', 'ISSUED', 'REDEEMED', 'EXPIRED', 'CANCELLED');

-- CreateEnum
CREATE TYPE "WebhookSource" AS ENUM ('MOLLIE', 'CRYPTO');

-- CreateEnum
CREATE TYPE "WebhookProcessingStatus" AS ENUM ('RECEIVED', 'PROCESSED', 'FAILED', 'SKIPPED_DUPLICATE');

-- CreateEnum
CREATE TYPE "AuditActorType" AS ENUM ('GUEST', 'STAFF', 'SYSTEM', 'MOLLIE_WEBHOOK');

-- CreateEnum
CREATE TYPE "DisputeType" AS ENUM ('CHARGEBACK', 'GUEST_COMPLAINT', 'REFUND_REQUEST');

-- CreateEnum
CREATE TYPE "DisputeStatus" AS ENUM ('OPEN', 'EVIDENCE_GATHERING', 'WON', 'LOST', 'CLOSED');

-- CreateEnum
CREATE TYPE "IncidentSeverity" AS ENUM ('SEV1', 'SEV2', 'SEV3', 'SEV4');

-- CreateEnum
CREATE TYPE "IncidentStatus" AS ENUM ('OPEN', 'MITIGATING', 'RESOLVED');

-- CreateTable
CREATE TABLE "restaurants" (
    "id" UUID NOT NULL,
    "slug" VARCHAR(64) NOT NULL,
    "legal_name" VARCHAR(255) NOT NULL,
    "trade_name" VARCHAR(255) NOT NULL,
    "kvk_number" VARCHAR(8),
    "vat_number" VARCHAR(14),
    "country_code" CHAR(2) NOT NULL DEFAULT 'NL',
    "default_currency" CHAR(3) NOT NULL DEFAULT 'EUR',
    "status" "RestaurantStatus" NOT NULL,
    "mollie_org_id" VARCHAR(32),
    "payments_enabled" BOOLEAN NOT NULL DEFAULT false,
    "settings_json" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,
    "deleted_at" TIMESTAMPTZ(6),

    CONSTRAINT "restaurants_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "venues" (
    "id" UUID NOT NULL,
    "restaurant_id" UUID NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "timezone" VARCHAR(64) NOT NULL DEFAULT 'Europe/Amsterdam',
    "address_line1" VARCHAR(255),
    "city" VARCHAR(128),
    "postal_code" VARCHAR(16),
    "geo_lat" DECIMAL(9,6),
    "geo_lng" DECIMAL(9,6),
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "venues_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tables" (
    "id" UUID NOT NULL,
    "venue_id" UUID NOT NULL,
    "table_code" VARCHAR(16) NOT NULL,
    "section" VARCHAR(64),
    "seats" SMALLINT,
    "sort_order" INTEGER NOT NULL DEFAULT 0,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "current_dining_session_id" UUID,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "tables_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "table_qr_codes" (
    "id" UUID NOT NULL,
    "table_id" UUID NOT NULL,
    "public_slug" VARCHAR(32) NOT NULL,
    "qr_payload_url" TEXT NOT NULL,
    "version" INTEGER NOT NULL DEFAULT 1,
    "rotated_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "table_qr_codes_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" UUID NOT NULL,
    "email" TEXT,
    "email_verified_at" TIMESTAMPTZ(6),
    "phone_e164" VARCHAR(16),
    "display_name" VARCHAR(64),
    "locale" VARCHAR(8) NOT NULL DEFAULT 'nl-NL',
    "status" "UserStatus" NOT NULL,
    "password_hash" TEXT,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ(6),

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "guest_devices" (
    "id" UUID NOT NULL,
    "fingerprint_hash" CHAR(64),
    "first_seen_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "last_seen_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" UUID,
    "ip_hash" CHAR(64),

    CONSTRAINT "guest_devices_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "staff_members" (
    "id" UUID NOT NULL,
    "restaurant_id" UUID NOT NULL,
    "venue_id" UUID,
    "user_id" UUID NOT NULL,
    "role" "StaffRole" NOT NULL,
    "employee_code" VARCHAR(32),
    "pin_hash" TEXT,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "invited_at" TIMESTAMPTZ(6),
    "last_login_at" TIMESTAMPTZ(6),

    CONSTRAINT "staff_members_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "staff_devices" (
    "id" UUID NOT NULL,
    "staff_member_id" UUID NOT NULL,
    "device_label" VARCHAR(64),
    "push_token" TEXT,
    "last_active_at" TIMESTAMPTZ(6) NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "staff_devices_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "dining_sessions" (
    "id" UUID NOT NULL,
    "table_id" UUID NOT NULL,
    "venue_id" UUID NOT NULL,
    "restaurant_id" UUID NOT NULL,
    "state" "DiningSessionState" NOT NULL,
    "party_size" SMALLINT,
    "opened_by_staff_id" UUID,
    "closed_by_staff_id" UUID,
    "opened_at" TIMESTAMPTZ(6) NOT NULL,
    "closed_at" TIMESTAMPTZ(6),
    "close_reason" "CloseReasonCode",
    "active_payment_session_id" UUID,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "dining_sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "payment_sessions" (
    "id" UUID NOT NULL,
    "dining_session_id" UUID NOT NULL,
    "bill_id" UUID NOT NULL,
    "state" "PaymentSessionState" NOT NULL,
    "join_pin" CHAR(6),
    "claims_frozen" BOOLEAN NOT NULL DEFAULT false,
    "opened_by_staff_id" UUID NOT NULL,
    "opened_at" TIMESTAMPTZ(6) NOT NULL,
    "completed_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "payment_sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "payment_session_tokens" (
    "id" UUID NOT NULL,
    "payment_session_id" UUID NOT NULL,
    "token_hash" CHAR(64) NOT NULL,
    "state" "TokenState" NOT NULL,
    "issued_at" TIMESTAMPTZ(6) NOT NULL,
    "expires_at" TIMESTAMPTZ(6) NOT NULL,
    "revoked_at" TIMESTAMPTZ(6),
    "rotation_reason" VARCHAR(32),
    "refresh_count" SMALLINT NOT NULL DEFAULT 0,

    CONSTRAINT "payment_session_tokens_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "participants" (
    "id" UUID NOT NULL,
    "payment_session_id" UUID NOT NULL,
    "guest_device_id" UUID NOT NULL,
    "user_id" UUID,
    "display_name" VARCHAR(32) NOT NULL,
    "state" "ParticipantState" NOT NULL,
    "joined_at" TIMESTAMPTZ(6) NOT NULL,
    "left_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "participants_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "menu_categories" (
    "id" UUID NOT NULL,
    "restaurant_id" UUID NOT NULL,
    "venue_id" UUID NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "sort_order" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "menu_categories_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "menu_items" (
    "id" UUID NOT NULL,
    "category_id" UUID NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "price_display_cents" INTEGER NOT NULL,
    "vat_rate_bps" INTEGER NOT NULL,
    "allergens_json" JSONB NOT NULL DEFAULT '[]',
    "is_available" BOOLEAN NOT NULL DEFAULT true,
    "sort_order" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "menu_items_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "orders" (
    "id" UUID NOT NULL,
    "dining_session_id" UUID NOT NULL,
    "external_pos_check_id" VARCHAR(64),
    "source" "OrderSource" NOT NULL,
    "status" "OrderStatus" NOT NULL,

    CONSTRAINT "orders_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "order_items" (
    "id" UUID NOT NULL,
    "order_id" UUID NOT NULL,
    "external_line_id" VARCHAR(64) NOT NULL,

    CONSTRAINT "order_items_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "bills" (
    "id" UUID NOT NULL,
    "dining_session_id" UUID NOT NULL,
    "restaurant_id" UUID NOT NULL,
    "currency" CHAR(3) NOT NULL DEFAULT 'EUR',
    "bill_version" INTEGER NOT NULL DEFAULT 1,
    "settlement_state" "BillSettlementState" NOT NULL,
    "menu_subtotal_cents" INTEGER NOT NULL DEFAULT 0,
    "service_charge_cents" INTEGER NOT NULL DEFAULT 0,
    "discount_cents" INTEGER NOT NULL DEFAULT 0,
    "bill_grand_total_cents" INTEGER NOT NULL,
    "allocated_cents" INTEGER NOT NULL DEFAULT 0,
    "confirmed_paid_cents" INTEGER NOT NULL DEFAULT 0,
    "unclaimed_cents" INTEGER NOT NULL DEFAULT 0,
    "active_checkout_count" INTEGER NOT NULL DEFAULT 0,
    "locked_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "bills_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "bill_lines" (
    "id" UUID NOT NULL,
    "bill_id" UUID NOT NULL,
    "line_kind" "BillLineKind" NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "qty" DECIMAL(8,3) NOT NULL,
    "unit_price_inc_vat_cents" INTEGER NOT NULL,
    "vat_rate_bps" INTEGER NOT NULL,
    "line_total_inc_vat_cents" INTEGER NOT NULL,
    "splittable" BOOLEAN NOT NULL DEFAULT false,
    "max_shares" SMALLINT,
    "menu_item_id" UUID,
    "order_item_id" UUID,
    "sort_order" INTEGER NOT NULL DEFAULT 0,
    "voided_at" TIMESTAMPTZ(6),

    CONSTRAINT "bill_lines_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "allocatable_units" (
    "id" UUID NOT NULL,
    "bill_line_id" UUID NOT NULL,
    "unit_index" SMALLINT NOT NULL,
    "unit_value_cents" INTEGER NOT NULL,
    "max_shares" SMALLINT NOT NULL DEFAULT 1,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "allocatable_units_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "allocations" (
    "id" UUID NOT NULL,
    "bill_id" UUID NOT NULL,
    "bill_version" INTEGER NOT NULL,
    "allocatable_unit_id" UUID NOT NULL,
    "participant_id" UUID NOT NULL,
    "split_mode" "SplitMode" NOT NULL,
    "share_numerator" SMALLINT NOT NULL DEFAULT 1,
    "share_denominator" SMALLINT NOT NULL DEFAULT 1,
    "allocated_amount_cents" INTEGER NOT NULL,
    "service_charge_share_cents" INTEGER NOT NULL DEFAULT 0,
    "equal_group_id" UUID,
    "custom_pledge_id" UUID,
    "state" "AllocationState" NOT NULL,
    "version" INTEGER NOT NULL DEFAULT 1,
    "committed_at" TIMESTAMPTZ(6),
    "released_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "allocations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "custom_pledges" (
    "id" UUID NOT NULL,
    "bill_id" UUID NOT NULL,
    "participant_id" UUID NOT NULL,
    "amount_cents" INTEGER NOT NULL,
    "state" "PledgeState" NOT NULL,

    CONSTRAINT "custom_pledges_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "checkout_intents" (
    "id" UUID NOT NULL,
    "payment_session_id" UUID NOT NULL,
    "participant_id" UUID NOT NULL,
    "bill_id" UUID NOT NULL,
    "bill_version" INTEGER NOT NULL,
    "subtotal_cents" INTEGER NOT NULL,
    "tip_cents" INTEGER NOT NULL DEFAULT 0,
    "checkout_total_cents" INTEGER NOT NULL,
    "allocation_snapshot_json" JSONB NOT NULL,
    "idempotency_key" VARCHAR(128) NOT NULL,
    "state" "CheckoutIntentState" NOT NULL,
    "expires_at" TIMESTAMPTZ(6) NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "checkout_intents_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "payment_intents" (
    "id" UUID NOT NULL,
    "checkout_intent_id" UUID NOT NULL,
    "payment_session_id" UUID NOT NULL,
    "participant_id" UUID NOT NULL,
    "restaurant_id" UUID NOT NULL,
    "mollie_payment_id" VARCHAR(32),
    "status" "PaymentIntentStatus" NOT NULL,
    "amount_cents" INTEGER NOT NULL,
    "currency" CHAR(3) NOT NULL,
    "method" VARCHAR(32),
    "idempotency_key" VARCHAR(128) NOT NULL,
    "bill_version" INTEGER NOT NULL,
    "metadata_json" JSONB NOT NULL DEFAULT '{}',
    "mollie_checkout_url" TEXT,
    "failure_reason" TEXT,
    "paid_at" TIMESTAMPTZ(6),
    "expires_at" TIMESTAMPTZ(6),
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "payment_intents_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "payments" (
    "id" UUID NOT NULL,
    "payment_intent_id" UUID NOT NULL,
    "mollie_payment_id" VARCHAR(32) NOT NULL,
    "restaurant_id" UUID NOT NULL,
    "payment_session_id" UUID NOT NULL,
    "participant_id" UUID NOT NULL,
    "amount_cents" INTEGER NOT NULL,
    "subtotal_share_cents" INTEGER NOT NULL,
    "tip_cents" INTEGER NOT NULL DEFAULT 0,
    "method" VARCHAR(32) NOT NULL,
    "paid_at" TIMESTAMPTZ(6) NOT NULL,
    "settlement_status" "SettlementStatus" NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "payments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tips" (
    "id" UUID NOT NULL,
    "checkout_intent_id" UUID NOT NULL,
    "payment_id" UUID,
    "basis_cents" INTEGER NOT NULL,
    "tip_cents" INTEGER NOT NULL,
    "tip_percent_bps" INTEGER,
    "destination" "TipDestination" NOT NULL,

    CONSTRAINT "tips_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "payment_refunds" (
    "id" UUID NOT NULL,
    "payment_id" UUID NOT NULL,
    "mollie_refund_id" VARCHAR(32) NOT NULL,
    "amount_cents" INTEGER NOT NULL,
    "status" "RefundStatus" NOT NULL,
    "initiated_by_staff_id" UUID,
    "reason" TEXT,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "payment_refunds_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "mollie_connections" (
    "id" UUID NOT NULL,
    "restaurant_id" UUID NOT NULL,
    "mollie_org_id" VARCHAR(32),
    "access_token_enc" BYTEA,
    "refresh_token_enc" BYTEA,
    "token_expires_at" TIMESTAMPTZ(6),
    "onboarding_status" VARCHAR(32),
    "scopes" TEXT[],
    "connected_at" TIMESTAMPTZ(6),

    CONSTRAINT "mollie_connections_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "rewards_accounts" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "points_balance" INTEGER NOT NULL DEFAULT 0,
    "lifetime_points" INTEGER NOT NULL DEFAULT 0,
    "status" "RewardsAccountStatus" NOT NULL,

    CONSTRAINT "rewards_accounts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "rewards_ledger_entries" (
    "id" UUID NOT NULL,
    "rewards_account_id" UUID NOT NULL,
    "entry_type" "RewardsEntryType" NOT NULL,
    "points_delta" INTEGER NOT NULL,
    "payment_id" UUID,
    "redemption_id" UUID,
    "idempotency_key" VARCHAR(128) NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "rewards_ledger_entries_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "partner_merchants" (
    "id" UUID NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "slug" VARCHAR(64) NOT NULL,
    "status" VARCHAR(32) NOT NULL,
    "settlement_config_json" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "partner_merchants_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "redemptions" (
    "id" UUID NOT NULL,
    "rewards_account_id" UUID NOT NULL,
    "partner_merchant_id" UUID NOT NULL,
    "offer_id" UUID NOT NULL,
    "points_spent" INTEGER NOT NULL,
    "voucher_code_hash" CHAR(64) NOT NULL,
    "status" "RedemptionStatus" NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "redemptions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "service_signals" (
    "id" UUID NOT NULL,
    "table_id" UUID NOT NULL,
    "guest_device_id" UUID NOT NULL,
    "signal_type" "ServiceSignalType" NOT NULL,
    "status" "ServiceSignalStatus" NOT NULL,
    "cooldown_until" TIMESTAMPTZ(6),
    "acknowledged_by_staff_id" UUID,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "service_signals_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "audit_log_entries" (
    "id" UUID NOT NULL,
    "restaurant_id" UUID,
    "occurred_at" TIMESTAMPTZ(6) NOT NULL,
    "actor_type" "AuditActorType" NOT NULL,
    "actor_id" UUID,
    "action" VARCHAR(64) NOT NULL,
    "resource_type" VARCHAR(64) NOT NULL,
    "resource_id" UUID NOT NULL,
    "correlation_id" UUID,
    "payload_json" JSONB NOT NULL DEFAULT '{}',
    "ip_hash" CHAR(64),

    CONSTRAINT "audit_log_entries_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "webhook_events" (
    "id" UUID NOT NULL,
    "source" "WebhookSource" NOT NULL,
    "external_id" VARCHAR(128) NOT NULL,
    "idempotency_key" VARCHAR(256) NOT NULL,
    "payload_json" JSONB NOT NULL,
    "signature_valid" BOOLEAN,
    "processing_status" "WebhookProcessingStatus" NOT NULL,
    "processed_at" TIMESTAMPTZ(6),
    "error_message" TEXT,
    "received_at" TIMESTAMPTZ(6) NOT NULL,

    CONSTRAINT "webhook_events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "disputes" (
    "id" UUID NOT NULL,
    "payment_id" UUID NOT NULL,
    "restaurant_id" UUID NOT NULL,
    "dispute_type" "DisputeType" NOT NULL,
    "status" "DisputeStatus" NOT NULL,
    "mollie_chargeback_id" VARCHAR(32),
    "amount_cents" INTEGER NOT NULL,
    "assigned_ops_user_id" UUID,
    "resolution_notes" TEXT,
    "opened_at" TIMESTAMPTZ(6) NOT NULL,
    "closed_at" TIMESTAMPTZ(6),

    CONSTRAINT "disputes_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "incidents" (
    "id" UUID NOT NULL,
    "severity" "IncidentSeverity" NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT NOT NULL,
    "restaurant_id" UUID,
    "status" "IncidentStatus" NOT NULL,
    "started_at" TIMESTAMPTZ(6) NOT NULL,
    "resolved_at" TIMESTAMPTZ(6),

    CONSTRAINT "incidents_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "bill_state_events" (
    "id" UUID NOT NULL,
    "bill_id" UUID NOT NULL,
    "from_state" "BillSettlementState" NOT NULL,
    "to_state" "BillSettlementState" NOT NULL,
    "trigger" VARCHAR(64) NOT NULL,
    "actor_staff_id" UUID,
    "occurred_at" TIMESTAMPTZ(6) NOT NULL,
    "metadata_json" JSONB NOT NULL DEFAULT '{}',

    CONSTRAINT "bill_state_events_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "restaurants_slug_key" ON "restaurants"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "tables_venue_id_table_code_key" ON "tables"("venue_id", "table_code");

-- CreateIndex
CREATE UNIQUE INDEX "table_qr_codes_table_id_key" ON "table_qr_codes"("table_id");

-- CreateIndex
CREATE UNIQUE INDEX "table_qr_codes_public_slug_key" ON "table_qr_codes"("public_slug");

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "users_phone_e164_key" ON "users"("phone_e164");

-- CreateIndex
CREATE UNIQUE INDEX "staff_members_restaurant_id_user_id_key" ON "staff_members"("restaurant_id", "user_id");

-- CreateIndex
CREATE UNIQUE INDEX "payment_sessions_bill_id_key" ON "payment_sessions"("bill_id");

-- CreateIndex
CREATE UNIQUE INDEX "payment_session_tokens_token_hash_key" ON "payment_session_tokens"("token_hash");

-- CreateIndex
CREATE UNIQUE INDEX "allocatable_units_bill_line_id_unit_index_key" ON "allocatable_units"("bill_line_id", "unit_index");

-- CreateIndex
CREATE UNIQUE INDEX "checkout_intents_idempotency_key_key" ON "checkout_intents"("idempotency_key");

-- CreateIndex
CREATE UNIQUE INDEX "payment_intents_checkout_intent_id_key" ON "payment_intents"("checkout_intent_id");

-- CreateIndex
CREATE UNIQUE INDEX "payment_intents_mollie_payment_id_key" ON "payment_intents"("mollie_payment_id");

-- CreateIndex
CREATE UNIQUE INDEX "payment_intents_idempotency_key_key" ON "payment_intents"("idempotency_key");

-- CreateIndex
CREATE UNIQUE INDEX "payments_payment_intent_id_key" ON "payments"("payment_intent_id");

-- CreateIndex
CREATE UNIQUE INDEX "payments_mollie_payment_id_key" ON "payments"("mollie_payment_id");

-- CreateIndex
CREATE UNIQUE INDEX "tips_checkout_intent_id_key" ON "tips"("checkout_intent_id");

-- CreateIndex
CREATE UNIQUE INDEX "tips_payment_id_key" ON "tips"("payment_id");

-- CreateIndex
CREATE UNIQUE INDEX "payment_refunds_mollie_refund_id_key" ON "payment_refunds"("mollie_refund_id");

-- CreateIndex
CREATE UNIQUE INDEX "mollie_connections_restaurant_id_key" ON "mollie_connections"("restaurant_id");

-- CreateIndex
CREATE UNIQUE INDEX "rewards_accounts_user_id_key" ON "rewards_accounts"("user_id");

-- CreateIndex
CREATE UNIQUE INDEX "rewards_ledger_entries_idempotency_key_key" ON "rewards_ledger_entries"("idempotency_key");

-- CreateIndex
CREATE UNIQUE INDEX "partner_merchants_slug_key" ON "partner_merchants"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "webhook_events_idempotency_key_key" ON "webhook_events"("idempotency_key");

-- AddForeignKey
ALTER TABLE "venues" ADD CONSTRAINT "venues_restaurant_id_fkey" FOREIGN KEY ("restaurant_id") REFERENCES "restaurants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tables" ADD CONSTRAINT "tables_venue_id_fkey" FOREIGN KEY ("venue_id") REFERENCES "venues"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tables" ADD CONSTRAINT "tables_current_dining_session_id_fkey" FOREIGN KEY ("current_dining_session_id") REFERENCES "dining_sessions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "table_qr_codes" ADD CONSTRAINT "table_qr_codes_table_id_fkey" FOREIGN KEY ("table_id") REFERENCES "tables"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "guest_devices" ADD CONSTRAINT "guest_devices_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "staff_members" ADD CONSTRAINT "staff_members_restaurant_id_fkey" FOREIGN KEY ("restaurant_id") REFERENCES "restaurants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "staff_members" ADD CONSTRAINT "staff_members_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "staff_devices" ADD CONSTRAINT "staff_devices_staff_member_id_fkey" FOREIGN KEY ("staff_member_id") REFERENCES "staff_members"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "dining_sessions" ADD CONSTRAINT "dining_sessions_table_id_fkey" FOREIGN KEY ("table_id") REFERENCES "tables"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "dining_sessions" ADD CONSTRAINT "dining_sessions_venue_id_fkey" FOREIGN KEY ("venue_id") REFERENCES "venues"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "dining_sessions" ADD CONSTRAINT "dining_sessions_restaurant_id_fkey" FOREIGN KEY ("restaurant_id") REFERENCES "restaurants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "dining_sessions" ADD CONSTRAINT "dining_sessions_opened_by_staff_id_fkey" FOREIGN KEY ("opened_by_staff_id") REFERENCES "staff_members"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "dining_sessions" ADD CONSTRAINT "dining_sessions_closed_by_staff_id_fkey" FOREIGN KEY ("closed_by_staff_id") REFERENCES "staff_members"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "dining_sessions" ADD CONSTRAINT "dining_sessions_active_payment_session_id_fkey" FOREIGN KEY ("active_payment_session_id") REFERENCES "payment_sessions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_sessions" ADD CONSTRAINT "payment_sessions_dining_session_id_fkey" FOREIGN KEY ("dining_session_id") REFERENCES "dining_sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_sessions" ADD CONSTRAINT "payment_sessions_bill_id_fkey" FOREIGN KEY ("bill_id") REFERENCES "bills"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_sessions" ADD CONSTRAINT "payment_sessions_opened_by_staff_id_fkey" FOREIGN KEY ("opened_by_staff_id") REFERENCES "staff_members"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_session_tokens" ADD CONSTRAINT "payment_session_tokens_payment_session_id_fkey" FOREIGN KEY ("payment_session_id") REFERENCES "payment_sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "participants" ADD CONSTRAINT "participants_payment_session_id_fkey" FOREIGN KEY ("payment_session_id") REFERENCES "payment_sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "participants" ADD CONSTRAINT "participants_guest_device_id_fkey" FOREIGN KEY ("guest_device_id") REFERENCES "guest_devices"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "participants" ADD CONSTRAINT "participants_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "menu_categories" ADD CONSTRAINT "menu_categories_restaurant_id_fkey" FOREIGN KEY ("restaurant_id") REFERENCES "restaurants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "menu_categories" ADD CONSTRAINT "menu_categories_venue_id_fkey" FOREIGN KEY ("venue_id") REFERENCES "venues"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "menu_items" ADD CONSTRAINT "menu_items_category_id_fkey" FOREIGN KEY ("category_id") REFERENCES "menu_categories"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "orders" ADD CONSTRAINT "orders_dining_session_id_fkey" FOREIGN KEY ("dining_session_id") REFERENCES "dining_sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "order_items" ADD CONSTRAINT "order_items_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "orders"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "bills" ADD CONSTRAINT "bills_dining_session_id_fkey" FOREIGN KEY ("dining_session_id") REFERENCES "dining_sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "bills" ADD CONSTRAINT "bills_restaurant_id_fkey" FOREIGN KEY ("restaurant_id") REFERENCES "restaurants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "bill_lines" ADD CONSTRAINT "bill_lines_bill_id_fkey" FOREIGN KEY ("bill_id") REFERENCES "bills"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "bill_lines" ADD CONSTRAINT "bill_lines_menu_item_id_fkey" FOREIGN KEY ("menu_item_id") REFERENCES "menu_items"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "bill_lines" ADD CONSTRAINT "bill_lines_order_item_id_fkey" FOREIGN KEY ("order_item_id") REFERENCES "order_items"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "allocatable_units" ADD CONSTRAINT "allocatable_units_bill_line_id_fkey" FOREIGN KEY ("bill_line_id") REFERENCES "bill_lines"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "allocations" ADD CONSTRAINT "allocations_bill_id_fkey" FOREIGN KEY ("bill_id") REFERENCES "bills"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "allocations" ADD CONSTRAINT "allocations_allocatable_unit_id_fkey" FOREIGN KEY ("allocatable_unit_id") REFERENCES "allocatable_units"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "allocations" ADD CONSTRAINT "allocations_participant_id_fkey" FOREIGN KEY ("participant_id") REFERENCES "participants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "allocations" ADD CONSTRAINT "allocations_custom_pledge_id_fkey" FOREIGN KEY ("custom_pledge_id") REFERENCES "custom_pledges"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "custom_pledges" ADD CONSTRAINT "custom_pledges_bill_id_fkey" FOREIGN KEY ("bill_id") REFERENCES "bills"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "custom_pledges" ADD CONSTRAINT "custom_pledges_participant_id_fkey" FOREIGN KEY ("participant_id") REFERENCES "participants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "checkout_intents" ADD CONSTRAINT "checkout_intents_payment_session_id_fkey" FOREIGN KEY ("payment_session_id") REFERENCES "payment_sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "checkout_intents" ADD CONSTRAINT "checkout_intents_participant_id_fkey" FOREIGN KEY ("participant_id") REFERENCES "participants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_intents" ADD CONSTRAINT "payment_intents_checkout_intent_id_fkey" FOREIGN KEY ("checkout_intent_id") REFERENCES "checkout_intents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_intents" ADD CONSTRAINT "payment_intents_payment_session_id_fkey" FOREIGN KEY ("payment_session_id") REFERENCES "payment_sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_intents" ADD CONSTRAINT "payment_intents_participant_id_fkey" FOREIGN KEY ("participant_id") REFERENCES "participants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_intents" ADD CONSTRAINT "payment_intents_restaurant_id_fkey" FOREIGN KEY ("restaurant_id") REFERENCES "restaurants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payments" ADD CONSTRAINT "payments_payment_intent_id_fkey" FOREIGN KEY ("payment_intent_id") REFERENCES "payment_intents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payments" ADD CONSTRAINT "payments_restaurant_id_fkey" FOREIGN KEY ("restaurant_id") REFERENCES "restaurants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payments" ADD CONSTRAINT "payments_payment_session_id_fkey" FOREIGN KEY ("payment_session_id") REFERENCES "payment_sessions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payments" ADD CONSTRAINT "payments_participant_id_fkey" FOREIGN KEY ("participant_id") REFERENCES "participants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tips" ADD CONSTRAINT "tips_checkout_intent_id_fkey" FOREIGN KEY ("checkout_intent_id") REFERENCES "checkout_intents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tips" ADD CONSTRAINT "tips_payment_id_fkey" FOREIGN KEY ("payment_id") REFERENCES "payments"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_refunds" ADD CONSTRAINT "payment_refunds_payment_id_fkey" FOREIGN KEY ("payment_id") REFERENCES "payments"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_refunds" ADD CONSTRAINT "payment_refunds_initiated_by_staff_id_fkey" FOREIGN KEY ("initiated_by_staff_id") REFERENCES "staff_members"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "mollie_connections" ADD CONSTRAINT "mollie_connections_restaurant_id_fkey" FOREIGN KEY ("restaurant_id") REFERENCES "restaurants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "rewards_accounts" ADD CONSTRAINT "rewards_accounts_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "rewards_ledger_entries" ADD CONSTRAINT "rewards_ledger_entries_rewards_account_id_fkey" FOREIGN KEY ("rewards_account_id") REFERENCES "rewards_accounts"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "rewards_ledger_entries" ADD CONSTRAINT "rewards_ledger_entries_payment_id_fkey" FOREIGN KEY ("payment_id") REFERENCES "payments"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "rewards_ledger_entries" ADD CONSTRAINT "rewards_ledger_entries_redemption_id_fkey" FOREIGN KEY ("redemption_id") REFERENCES "redemptions"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "redemptions" ADD CONSTRAINT "redemptions_rewards_account_id_fkey" FOREIGN KEY ("rewards_account_id") REFERENCES "rewards_accounts"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "redemptions" ADD CONSTRAINT "redemptions_partner_merchant_id_fkey" FOREIGN KEY ("partner_merchant_id") REFERENCES "partner_merchants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "service_signals" ADD CONSTRAINT "service_signals_table_id_fkey" FOREIGN KEY ("table_id") REFERENCES "tables"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "service_signals" ADD CONSTRAINT "service_signals_guest_device_id_fkey" FOREIGN KEY ("guest_device_id") REFERENCES "guest_devices"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "service_signals" ADD CONSTRAINT "service_signals_acknowledged_by_staff_id_fkey" FOREIGN KEY ("acknowledged_by_staff_id") REFERENCES "staff_members"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "audit_log_entries" ADD CONSTRAINT "audit_log_entries_restaurant_id_fkey" FOREIGN KEY ("restaurant_id") REFERENCES "restaurants"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "audit_log_entries" ADD CONSTRAINT "audit_log_entries_actor_id_fkey" FOREIGN KEY ("actor_id") REFERENCES "staff_members"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "disputes" ADD CONSTRAINT "disputes_payment_id_fkey" FOREIGN KEY ("payment_id") REFERENCES "payments"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "disputes" ADD CONSTRAINT "disputes_restaurant_id_fkey" FOREIGN KEY ("restaurant_id") REFERENCES "restaurants"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_restaurant_id_fkey" FOREIGN KEY ("restaurant_id") REFERENCES "restaurants"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "bill_state_events" ADD CONSTRAINT "bill_state_events_bill_id_fkey" FOREIGN KEY ("bill_id") REFERENCES "bills"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

