import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "nl.rekentafel.waiter",
  appName: "Rekentafel Waiter",
  webDir: "../staff-web/dist",
  server: {
    androidScheme: "https",
  },
  ios: {
    contentInset: "automatic",
  },
};

export default config;
