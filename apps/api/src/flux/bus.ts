/**
 * FluxZero-inspired message bus for Rekentafel.
 * Handlers are pure business logic; HTTP routes dispatch messages here.
 */

export type MessageContext = {
  requestId: string;
  actor?: { type: "guest" | "staff" | "system" | "webhook"; id?: string };
};

export type MessageHandler<TMessage, TResult> = (
  message: TMessage,
  ctx: MessageContext,
) => Promise<TResult>;

type HandlerMap = Map<string, MessageHandler<unknown, unknown>>;

export class MessageBus {
  private readonly handlers: HandlerMap = new Map();

  register<TMessage extends { type: string }, TResult>(
    type: TMessage["type"],
    handler: MessageHandler<TMessage, TResult>,
  ): void {
    this.handlers.set(type, handler as MessageHandler<unknown, unknown>);
  }

  async dispatch<TMessage extends { type: string }, TResult>(
    message: TMessage,
    ctx: MessageContext,
  ): Promise<TResult> {
    const handler = this.handlers.get(message.type);
    if (!handler) {
      throw new Error(`No handler registered for message type: ${message.type}`);
    }
    return handler(message, ctx) as Promise<TResult>;
  }
}

export function createMessageBus(): MessageBus {
  return new MessageBus();
}
