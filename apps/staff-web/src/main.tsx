import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@rekentafel/ui-core/styles.css";
import "./app.css";
import { LoginShell } from "./pages/LoginShell";
import { FloorGrid } from "./pages/FloorGrid";
import { TableDetailPage } from "./pages/TableDetailPage";
import { QrDownloadPage } from "./pages/QrDownloadPage";
import type { StaffTable } from "@rekentafel/staff-hooks";

const queryClient = new QueryClient();

type View = "floor" | "table" | "qr";

function App() {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem("staff_token"),
  );
  const [selectedTable, setSelectedTable] = useState<StaffTable | null>(null);
  const [view, setView] = useState<View>("floor");

  if (!token) {
    return (
      <LoginShell
        onLogin={(t: string) => {
          localStorage.setItem("staff_token", t);
          setToken(t);
        }}
      />
    );
  }

  if (view === "qr") {
    return <QrDownloadPage onBack={() => setView("floor")} />;
  }

  if (selectedTable) {
    return (
      <TableDetailPage
        table={selectedTable}
        accessToken={token}
        onBack={() => setSelectedTable(null)}
      />
    );
  }

  return (
    <FloorGrid
      accessToken={token}
      onSelectTable={setSelectedTable}
      onOpenQr={() => setView("qr")}
      onLogout={() => {
        localStorage.removeItem("staff_token");
        setToken(null);
      }}
    />
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
