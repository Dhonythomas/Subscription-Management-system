import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import { Loading } from "./components/ui";
import CatalogPage from "./pages/CatalogPage";
import DashboardPage from "./pages/DashboardPage";
import InvoicesPage from "./pages/InvoicesPage";
import LoginPage from "./pages/LoginPage";
import PaymentsPage from "./pages/PaymentsPage";
import PlansPage from "./pages/PlansPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";
import SubscriptionsPage from "./pages/SubscriptionsPage";

function RequireAuth() {
  const { user, loading } = useAuth();
  if (loading) return <Loading label="Checking your session…" />;
  return user ? <Layout /> : <Navigate to="/login" replace />;
}

function RoleGate({ roles, children }) {
  const { user } = useAuth();
  return roles.includes(user.role) ? children : <Navigate to="/" replace />;
}

function HomePage() {
  const { user } = useAuth();
  return user.role === "customer" ? (
    <Navigate to="/subscriptions" replace />
  ) : (
    <DashboardPage />
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<RequireAuth />}>
        <Route index element={<HomePage />} />
        <Route
          path="catalog"
          element={
            <RoleGate roles={["admin", "staff"]}>
              <CatalogPage />
            </RoleGate>
          }
        />
        <Route
          path="plans"
          element={
            <RoleGate roles={["admin", "staff"]}>
              <PlansPage />
            </RoleGate>
          }
        />
        <Route path="subscriptions" element={<SubscriptionsPage />} />
        <Route path="invoices" element={<InvoicesPage />} />
        <Route
          path="payments"
          element={
            <RoleGate roles={["admin", "staff"]}>
              <PaymentsPage />
            </RoleGate>
          }
        />
        <Route path="profile" element={<ProfilePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
