export type Competitor = {
  id: string;
  name: string;
  url: string;
  niche: string;
  createdAt: string;
};

export type Snapshot = {
  id: string;
  competitorId: string;
  scrapedAt: string;
  prices: { label: string; value: string }[];
  reviews: { text: string; rating?: number }[];
};

export type Alert = {
  id: string;
  competitorId: string;
  field: string;
  oldValue: string;
  newValue: string;
  detectedAt: string;
};

const competitors: Competitor[] = [];
const snapshots: Snapshot[] = [];
const alerts: Alert[] = [];

let seq = 1;
const nextId = (prefix: string) => `${prefix}_${seq++}`;

export const store = {
  listCompetitors: () => [...competitors],
  addCompetitor: (name: string, url: string, niche: string) => {
    const c: Competitor = { id: nextId("comp"), name, url, niche, createdAt: new Date().toISOString() };
    competitors.push(c);
    return c;
  },
  getSnapshots: (competitorId: string) => snapshots.filter((s) => s.competitorId === competitorId),
  addSnapshot: (competitorId: string, prices: Snapshot["prices"], reviews: Snapshot["reviews"]) => {
    const s: Snapshot = { id: nextId("snap"), competitorId, scrapedAt: new Date().toISOString(), prices, reviews };
    snapshots.push(s);
    return s;
  },
  listAlerts: () => [...alerts].reverse(),
  addAlert: (competitorId: string, field: string, oldValue: string, newValue: string) => {
    const a: Alert = { id: nextId("alert"), competitorId, field, oldValue, newValue, detectedAt: new Date().toISOString() };
    alerts.push(a);
    return a;
  },
};
