import { createRootRoute, createRoute, Outlet } from "@tanstack/react-router";
import { WelcomePage } from "./pages/WelcomePage";
import { TableLandingPage } from "./pages/TableLandingPage";
import { BillShellPage } from "./pages/BillShellPage";
import { JoinPage } from "./pages/JoinPage";
import { CheckoutReturnPage } from "./pages/CheckoutReturnPage";

const rootRoute = createRootRoute({
  component: () => <Outlet />,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: WelcomePage,
});

const tableRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/t/$restaurantSlug/$tableCode",
  component: TableLandingPage,
});

const billRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/session/$paymentSessionId",
  component: BillShellPage,
});

const joinRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/session/$paymentSessionId/join",
  component: JoinPage,
});

const checkoutReturnRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/checkout/return",
  component: CheckoutReturnPage,
  validateSearch: (search: Record<string, unknown>) => ({
    session: typeof search.session === "string" ? search.session : undefined,
  }),
});

export const routeTree = rootRoute.addChildren([
  indexRoute,
  tableRoute,
  billRoute,
  joinRoute,
  checkoutReturnRoute,
]);
