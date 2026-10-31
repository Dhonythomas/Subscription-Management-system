import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: "",
    password: "",
    name: "",
    billing_email: "",
    billing_phone: "",
    billing_address: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  function update(field) {
    return (event) => setForm({ ...form, [field]: event.target.value });
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register(form);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell auth-shell-register">
      <section className="auth-story">
        <div className="brand brand-light">
          <div className="brand-mark">B</div>
          <div>
            <strong>Brightloop</strong>
            <span>Subscription OS</span>
          </div>
        </div>
        <div className="auth-story-copy">
          <span className="eyebrow">Customer portal</span>
          <h1>One place for every subscription you own.</h1>
          <p>
            Create your account to view subscriptions, download invoices, and keep
            billing details current.
          </p>
        </div>
        <div className="password-rules">
          <strong>Password rules</strong>
          <span>9+ characters, uppercase, lowercase, and a special character.</span>
        </div>
      </section>
      <section className="auth-panel">
        <div className="auth-form-wrap">
          <div className="eyebrow">Get started</div>
          <h2>Create your account</h2>
          <form onSubmit={submit} className="stack">
            <div className="form-grid">
              <label className="field">
                <span>Name</span>
                <input value={form.name} onChange={update("name")} required />
              </label>
              <label className="field">
                <span>Email</span>
                <input
                  type="email"
                  value={form.email}
                  onChange={update("email")}
                  autoComplete="email"
                  required
                />
              </label>
              <label className="field">
                <span>Password</span>
                <input
                  type="password"
                  value={form.password}
                  onChange={update("password")}
                  autoComplete="new-password"
                  required
                />
              </label>
              <label className="field">
                <span>Billing email</span>
                <input
                  type="email"
                  value={form.billing_email}
                  onChange={update("billing_email")}
                />
              </label>
              <label className="field">
                <span>Billing phone</span>
                <input value={form.billing_phone} onChange={update("billing_phone")} />
              </label>
              <label className="field field-span">
                <span>Billing address</span>
                <input value={form.billing_address} onChange={update("billing_address")} />
              </label>
            </div>
            {error && <div className="error-box">{error}</div>}
            <button className="btn btn-primary btn-wide" disabled={busy}>
              {busy ? "Creating account…" : "Create account"}
            </button>
          </form>
          <p className="auth-switch">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </section>
    </div>
  );
}
