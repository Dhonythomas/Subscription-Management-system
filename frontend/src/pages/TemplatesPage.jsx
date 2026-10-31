import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { money, rows } from "../lib/format";
import { Card, Empty, ErrorBox, Field, Loading, PageHeader, Table } from "../components/ui";

export default function TemplatesPage() {
  const [templates, setTemplates] = useState([]);
  const [plans, setPlans] = useState([]);
  const [form, setForm] = useState({ name: "", plan: "", validity_days: "30" });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [templateData, planData] = await Promise.all([
        api.get("/subscriptions/templates/"),
        api.get("/plans/"),
      ]);
      setTemplates(rows(templateData));
      setPlans(rows(planData));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(load, []);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/subscriptions/templates/", {
        ...form,
        plan: Number(form.plan),
        validity_days: Number(form.validity_days),
      });
      setForm({ name: "", plan: "", validity_days: "30" });
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const planLabel = (id) => {
    const plan = plans.find((item) => item.id === id);
    return plan ? `#${plan.id} · ${plan.period} · ${money(plan.price)}` : `Plan #${id}`;
  };

  return (
    <>
      <PageHeader
        eyebrow="Quotations"
        title="Quotation templates"
        description="Reusable starting points for quotes. Staff and admin can maintain templates."
      />
      <ErrorBox error={error} onRetry={load} />
      {loading ? (
        <Loading />
      ) : (
        <>
          <Card title="New template" subtitle="The validity window controls how long a quote stays usable.">
            <form onSubmit={submit} className="stack">
              <div className="form-grid">
                <Field label="Template name">
                  <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
                </Field>
                <Field label="Plan">
                  <select value={form.plan} onChange={(event) => setForm({ ...form, plan: event.target.value })} required>
                    <option value="">Select plan</option>
                    {plans.map((plan) => (
                      <option key={plan.id} value={plan.id}>{planLabel(plan.id)}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Validity days">
                  <input
                    type="number"
                    min="1"
                    value={form.validity_days}
                    onChange={(event) => setForm({ ...form, validity_days: event.target.value })}
                    required
                  />
                </Field>
              </div>
              <button className="btn btn-primary" disabled={busy}>Create template</button>
            </form>
          </Card>
          <Card title="Templates" subtitle={`${templates.length} templates`}>
            {templates.length === 0 ? (
              <Empty title="No templates yet" />
            ) : (
              <Table>
                <thead><tr><th>Name</th><th>Plan</th><th>Validity</th><th>Status</th></tr></thead>
                <tbody>
                  {templates.map((template) => (
                    <tr key={template.id}>
                      <td><strong>{template.name}</strong></td>
                      <td>{planLabel(template.plan)}</td>
                      <td>{template.validity_days} days</td>
                      <td>{template.is_active ? "Active" : "Inactive"}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>
        </>
      )}
    </>
  );
}
