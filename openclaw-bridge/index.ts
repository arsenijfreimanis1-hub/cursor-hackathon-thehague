import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const DEFAULT_URL = "http://127.0.0.1:8787";
const OPENCLAW_COMMANDS = new Set(["new", "reset", "stop", "help", "status"]);
const WHATSAPP_ENVELOPE = /^\[WhatsApp[^\]]*\]\s*(?:\([^)]*\))?:\s*/i;

type PluginConfig = {
  jarvisUrl?: string;
  channels?: string[];
};

function resolveConfig(raw: unknown): { jarvisUrl: string; channels: Set<string> | null } {
  const cfg = (raw && typeof raw === "object" ? raw : {}) as PluginConfig;
  const jarvisUrl = (cfg.jarvisUrl ?? process.env.JARVIS_CORE_URL ?? DEFAULT_URL).replace(/\/$/, "");
  const channels = Array.isArray(cfg.channels) && cfg.channels.length > 0
    ? new Set(cfg.channels.map((c) => c.toLowerCase()))
    : null;
  return { jarvisUrl, channels };
}

function isSlashCommand(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed.startsWith("/")) return false;
  const cmd = trimmed.slice(1).split(/\s+/)[0]?.toLowerCase() ?? "";
  return OPENCLAW_COMMANDS.has(cmd);
}

function matchesChannel(channel: string, allowed: Set<string> | null): boolean {
  if (!allowed) return true;
  const c = channel.toLowerCase();
  if (allowed.has(c)) return true;
  if (allowed.has("whatsapp") && (c === "web" || c.includes("whatsapp"))) return true;
  return false;
}

function extractMessageText(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  const withoutEnvelope = trimmed.replace(WHATSAPP_ENVELOPE, "").trim();
  return withoutEnvelope || trimmed;
}

async function fetchJarvisReply(
  jarvisUrl: string,
  text: string,
  source: string,
): Promise<string> {
  const resp = await fetch(`${jarvisUrl}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text, source }),
    signal: AbortSignal.timeout(90_000),
  });
  if (!resp.ok) {
    return `JarvisCore error (${resp.status}). Check ${jarvisUrl}`;
  }
  const data = (await resp.json()) as { reply?: string; error?: string };
  return data.reply ?? data.error ?? "No response from William Agent.";
}

export default definePluginEntry({
  id: "jarvis-bridge",
  name: "Jarvis Bridge",
  description: "Forward inbound messages to JarvisCore (William Agent)",
  register(api) {
    const resolveState = () => resolveConfig(api.pluginConfig);

    const bridgeMessage = async (
      text: string,
      channel: string,
      senderId?: string,
    ): Promise<string> => {
      const { jarvisUrl } = resolveState();
      const cleaned = extractMessageText(text);
      if (!cleaned || isSlashCommand(cleaned)) {
        return "";
      }
      const source = channel ? `${channel}:${senderId ?? "unknown"}` : "openclaw";
      return fetchJarvisReply(jarvisUrl, cleaned, source);
    };

    // WhatsApp does not use generic inbound_claim — intercept before the OpenClaw agent runs.
    api.on(
      "before_agent_run",
      async (event, ctx) => {
        const channel = (ctx.channelId ?? "").toLowerCase();
        const { channels } = resolveState();
        if (!matchesChannel(channel, channels)) return;

        const text = extractMessageText(event.prompt ?? "");
        if (!text || isSlashCommand(text)) return;

        try {
          const reply = await bridgeMessage(text, channel, ctx.senderId);
          if (!reply) return;
          return {
            outcome: "block" as const,
            reason: "jarvis_bridge_handled",
            message: reply,
          };
        } catch (err) {
          api.logger.warn?.(`jarvis-bridge before_agent_run: ${String(err)}`);
          return {
            outcome: "block" as const,
            reason: "jarvis_bridge_offline",
            message: "William Agent is offline. Is JarvisCore running on port 8787?",
          };
        }
      },
      { priority: 200 },
    );

    // Fallback for channels that do use plugin-owned inbound_claim bindings.
    api.on(
      "inbound_claim",
      async (event, ctx) => {
        const channel = (event.channel ?? ctx.channelId ?? "").toLowerCase();
        const { channels } = resolveState();
        if (!matchesChannel(channel, channels)) return;

        const text = (event.bodyForAgent ?? event.content ?? "").trim();
        if (!text || isSlashCommand(text)) return;

        try {
          const reply = await bridgeMessage(text, channel, event.senderId ?? ctx.senderId);
          if (!reply) return;
          return { handled: true, reply: { text: reply } };
        } catch (err) {
          api.logger.warn?.(`jarvis-bridge inbound_claim: ${String(err)}`);
          return {
            handled: true,
            reply: { text: "William Agent is offline. Is JarvisCore running on port 8787?" },
          };
        }
      },
      { priority: 200 },
    );
  },
});
