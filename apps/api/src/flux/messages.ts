export type ResolveTableQrQuery = {
  type: "query.resolveTableQr";
  restaurantSlug: string;
  tableCode: string;
};

export type ListStaffTablesQuery = {
  type: "query.listStaffTables";
  venueId: string;
};

export type JoinPaymentSessionCommand = {
  type: "command.joinPaymentSession";
  paymentSessionId?: string;
  joinToken?: string;
  joinPin?: string;
  displayName: string;
  deviceFingerprint?: string;
};

export type GetPaymentSessionQuery = {
  type: "query.getPaymentSession";
  paymentSessionId: string;
  participantId?: string;
};

export type CreateClaimCommand = {
  type: "command.createClaim";
  paymentSessionId: string;
  participantId: string;
  billLineId: string;
  splitMode: "ITEM" | "SHARED";
  shareNumerator?: number;
  shareDenominator?: number;
  billVersion: number;
};

export type OpenDiningSessionCommand = {
  type: "command.openDiningSession";
  tableId: string;
  partySize?: number;
};

export type CloseDiningSessionCommand = {
  type: "command.closeDiningSession";
  tableId: string;
  diningSessionId: string;
  reason?: string;
};

export type AddBillLineCommand = {
  type: "command.addBillLine";
  tableId: string;
  name: string;
  qty: number;
  unitPriceIncVatCents: number;
  vatRateBps: number;
  lineKind?: "MENU_ITEM" | "SERVICE_CHARGE" | "MANUAL_MISC";
  splittable?: boolean;
};

export type ActivatePaymentModeCommand = {
  type: "command.activatePaymentMode";
  tableId: string;
};

export type CallServerCommand = {
  type: "command.callServer";
  tableId: string;
  guestDeviceId?: string;
  signalType: "ASSISTANCE" | "READY_TO_ORDER";
};

export type ListServiceSignalsQuery = {
  type: "query.listServiceSignals";
  venueId: string;
};

export type AckServiceSignalCommand = {
  type: "command.ackServiceSignal";
  signalId: string;
};

export type GetTableBillQuery = {
  type: "query.getTableBill";
  tableId: string;
};

export type ListStaffFloorQuery = {
  type: "query.listStaffFloor";
  venueId: string;
};

export type UpdateTableLayoutCommand = {
  type: "command.updateTableLayout";
  venueId: string;
  tableId: string;
  posX: number;
  posY: number;
};

export type UpdateTableStateCommand = {
  type: "command.updateTableState";
  tableId: string;
  state?: "SEATED" | "ORDERED" | "READY_TO_PAY" | "PAID" | "CLOSED";
  partySize?: number;
};

export type InitiateCombinedCheckoutCommand = {
  type: "command.initiateCombinedCheckout";
  paymentSessionId: string;
  participantId: string;
  tipCents?: number;
  redirectUrl: string;
};

export type ReconcileMollieWebhookCommand = {
  type: "command.reconcileMollieWebhook";
  molliePaymentId: string;
};

export type ApiMessage =
  | ResolveTableQrQuery
  | ListStaffTablesQuery
  | JoinPaymentSessionCommand
  | GetPaymentSessionQuery
  | CreateClaimCommand
  | OpenDiningSessionCommand
  | CloseDiningSessionCommand
  | AddBillLineCommand
  | ActivatePaymentModeCommand
  | CallServerCommand
  | ListServiceSignalsQuery
  | AckServiceSignalCommand
  | GetTableBillQuery
  | ListStaffFloorQuery
  | UpdateTableLayoutCommand
  | UpdateTableStateCommand
  | InitiateCombinedCheckoutCommand
  | ReconcileMollieWebhookCommand;
