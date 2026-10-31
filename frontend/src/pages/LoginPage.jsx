import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const demoAccounts = [
  ["Admin", "admin@example.com"],
  ["Staff", "staff@example.com"],
  ["Customer", "customer@example.com"],
];

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell">
      <section className="auth-story">
        <div className="brand brand-light">
          <div className="brand-mark">B</div>
          <div>
            <strong>Brightloop</strong>
            <span>Subscription OS</span>
          </div>
        </div>
        <div className="auth-story-copy">
          <span className="eyebrow">Run the full billing lifecycle</span>
          <h1>Products, plans, subscriptions, invoices, payments.</h1>
          <p>
            One calm workspace for recurring revenue. Every state change is
            audited, billing is idempotent, and customers only see their own data.
          </p>
        </div>
        <div className="auth-stat-row">
          <div>
            <strong>100%</strong>
            <span>backend tested</span>
          </div>
          <div>
            <strong>9</strong>
            <span>delivery phases</span>
          </div>
          <div>
            <strong>Zero</strong>
            <span>double billing</span>
          </div>
        </div>
      </section>
      <section className="auth-panel">
        <div className="auth-form-wrap">
          <div className="eyebrow">Welcome back</div>
          <h2>Sign in to Brightloop</h2>
          <p className="muted">Use a demo account or your customer credentials.</p>
          <form onSubmit={submit} className="stack">
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                required
              />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </label>
            {error && <div className="error-box">{error}</div>}
            <button className="btn btn-primary btn-wide" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <div className="demo-accounts">
            {demoAccounts.map(([role, account]) => (
              <button
                type="button"
                key={role}
                className="demo-account"
                onClick={() => {
                  setEmail(account);
                  setPassword("DemoPassword123!");
                }}
              >
                <span>{role}</span>
                <small>{account}</small>
              </button>
            ))}
          </div>
          <p className="auth-switch">
            New customer? <Link to="/register">Create an account</Link>
          </p>
        </div>
      </section>
    </div>
  );
}
