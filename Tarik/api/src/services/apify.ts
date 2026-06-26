const APIFY_BASE = "https://api.apify.com/v2";

export async function checkApify(token: string): Promise<{ ok: boolean; username?: string; error?: string }> {
  try {
    const res = await fetch(`${APIFY_BASE}/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    const data = (await res.json()) as { data?: { username?: string }; username?: string };
    return { ok: true, username: data.data?.username ?? data.username };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "unknown" };
  }
}

export async function runActor(
  token: string,
  actorId: string,
  input: Record<string, unknown>
): Promise<{ ok: boolean; runId?: string; error?: string }> {
  try {
    const res = await fetch(`${APIFY_BASE}/acts/${actorId}/runs`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    });
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    const data = (await res.json()) as { data?: { id?: string } };
    return { ok: true, runId: data.data?.id };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "unknown" };
  }
}
