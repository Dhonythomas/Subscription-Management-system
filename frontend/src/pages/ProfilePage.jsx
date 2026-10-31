import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import { title } from "../lib/format";
import { Card, ErrorBox, Field, Loading, PageHeader } from "../components/ui";

export default function ProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({
    name: "",
    billing_email: "",
    billing_address: "",
    billing_phone: "",
  });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  function sync(profileData) {
    setProfile(profileData);
    if (profileData.customer) {
      setForm({
        name: profileData.customer.name || "",
        billing_email: profileData.customer.billing_email || "",
        billing_address: profileData.customer.billing_address || "",
        billing_phone: profileData.customer.billing_phone || "",
      });
    }
  }

  async function load() {
    setLoading(true);
    setError(null);
    try {
      sync(await api.get("/accounts/me/"));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(load, []);

  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      sync(await api.patch("/accounts/me/", form));
      setSaved(true);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Account"
        title="Profile"
        description="Your identity and billing details. Customers can update only their own billing information."
      />
      <ErrorBox error={error} onRetry={load} />
      {loading ? (
        <Loading />
      ) : (
        profile && (
          <div className="profile-grid">
            <Card title="Account" subtitle="Role is enforced by the backend on every endpoint.">
              <dl className="detail-list">
                <div><dt>Email</dt><dd>{profile.email}</dd></div>
                <div><dt>Role</dt><dd>{title(profile.role)}</dd></div>
                <div><dt>User ID</dt><dd>#{profile.id}</dd></div>
                {profile.customer && <div><dt>Customer ID</dt><dd>#{profile.customer.id}</dd></div>}
              </dl>
            </Card>
            {user.role === "customer" && profile.customer && (
              <Card title="Billing details" subtitle="Used on invoices and receipts.">
                <form onSubmit={save} className="stack">
                  <Field label="Name">
                    <input
                      value={form.name}
                      onChange={(event) => setForm({ ...form, name: event.target.value })}
                      required
                    />
                  </Field>
                  <Field label="Billing email">
                    <input
                      type="email"
                      value={form.billing_email}
                      onChange={(event) => setForm({ ...form, billing_email: event.target.value })}
                    />
                  </Field>
                  <Field label="Billing phone">
                    <input
                      value={form.billing_phone}
                      onChange={(event) => setForm({ ...form, billing_phone: event.target.value })}
                    />
                  </Field>
                  <Field label="Billing address">
                    <input
                      value={form.billing_address}
                      onChange={(event) => setForm({ ...form, billing_address: event.target.value })}
                    />
                  </Field>
                  {saved && <div className="success-box">Profile updated.</div>}
                  <button className="btn btn-primary" disabled={busy}>Save changes</button>
                </form>
              </Card>
            )}
          </div>
        )
      )}
    </>
  );
}
