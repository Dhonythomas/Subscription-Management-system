import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const navigation = {
  admin: [
    ["/", "Overview"],
    ["/catalog", "Catalog"],
    ["/plans", "Plans"],
    ["/subscriptions", "Subscriptions"],
    ["/invoices", "Invoices"],
    ["/payments", "Payments"],
    ["/profile", "Profile"],
  ],
  staff: [
    ["/", "Overview"],
    ["/catalog", "Catalog"],
    ["/plans", "Plans"],
    ["/subscriptions", "Subscriptions"],
    ["/invoices", "Invoices"],
    ["/payments", "Payments"],
    ["/profile", "Profile"],
  ],
  customer: [
    ["/subscriptions", "My subscriptions"],
    ["/invoices", "My invoices"],
    ["/profile", "Profile"],
  ],
};

export default function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const links = navigation[user.role] || [];

  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">B</div>
          <div>
            <strong>Brightloop</strong>
            <span>Subscription OS</span>
          </div>
        </div>
        <nav>
          {links.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setOpen(false)}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              <span className="nav-dot" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="avatar">{user.email.slice(0, 1).toUpperCase()}</div>
          <div className="sidebar-user">
            <strong>{user.email}</strong>
            <span>{user.role}</span>
          </div>
          <button type="button" className="icon-button" onClick={logout} title="Log out">
            ↗
          </button>
        </div>
      </aside>
      {open && <button className="scrim" aria-label="Close menu" onClick={() => setOpen(false)} />}
      <main className="main">
        <header className="topbar">
          <button type="button" className="menu-button" onClick={() => setOpen(true)}>
            ☰
          </button>
          <span className="topbar-note">Brightloop Software · Billing operations</span>
          <span className="role-chip">{user.role}</span>
        </header>
        <div className="content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
