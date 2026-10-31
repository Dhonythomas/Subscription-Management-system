import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import { date, money, rows } from "../lib/format";
import { Card, Empty, ErrorBox, Field, Loading, PageHeader, Table } from "../components/ui";

const today = () => new Date().toISOString().slice(0, 10);
const nextYear = () => {
  const value = new Date();
  value.setFullYear(value.getFullYear() + 1);
  return value.toISOString().slice(0, 10);
};

const emptyPlan = {
  product: "",
  price: "",
  period: "monthly",
  min_qty: "1",
  start_date: today(),
  end_date: nextYear(),
  auto_close: false,
  closable: true,
  pausable: true,
  renewable: true,
};

export default function PlansPage() {
  const { user } = useAuth();
  const isAdmin = user.role === "admin";
  const [plans, setPlans] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(emptyPlan);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [planData, productData] = await Promise.all([
        api.get("/plans/"),
        api.get("/catalog/products/"),
      ]);
      setPlans(rows(planData));
      setProducts(rows(productData));
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
      await api.post("/plans/", form);
      setForm({ ...emptyPlan, start_date: today(), end_date: nextYear() });
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const productName = (id) => products.find((product) => product.id === id)?.name || `Product #${id}`;

  return (
    <>
      <PageHeader
        eyebrow="Plans"
        title="Subscription plans"
        description="Price, billing period, and the lifecycle rules that subscriptions inherit."
      />
      <ErrorBox error={error} onRetry={load} />
      {loading ? (
        <Loading />
      ) : (
        <>
          {isAdmin && (
            <Card title="New plan" subtitle="Admin-only write. Flags control pause, close, and renewal.">
              <form onSubmit={submit} className="stack">
                <div className="form-grid">
                  <Field label="Product">
                    <select
                      value={form.product}
                      onChange={(event) => setForm({ ...form, product: event.target.value })}
                      required
                    >
                      <option value="">Select product</option>
                      {products.map((product) => (
                        <option key={product.id} value={product.id}>{product.name}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Price">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={form.price}
                      onChange={(event) => setForm({ ...form, price: event.target.value })}
                      required
                    />
                  </Field>
                  <Field label="Period">
                    <select
                      value={form.period}
                      onChange={(event) => setForm({ ...form, period: event.target.value })}
                    >
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                      <option value="yearly">Yearly</option>
                    </select>
                  </Field>
                  <Field label="Minimum quantity">
                    <input
                      type="number"
                      min="1"
                      value={form.min_qty}
                      onChange={(event) => setForm({ ...form, min_qty: event.target.value })}
                      required
                    />
                  </Field>
                  <Field label="Start date">
                    <input
                      type="date"
                      value={form.start_date}
                      onChange={(event) => setForm({ ...form, start_date: event.target.value })}
                      required
                    />
                  </Field>
                  <Field label="End date">
                    <input
                      type="date"
                      value={form.end_date}
                      onChange={(event) => setForm({ ...form, end_date: event.target.value })}
                    />
                  </Field>
                </div>
                <div className="flag-row">
                  {[
                    ["pausable", "Pausable"],
                    ["closable", "Closable"],
                    ["renewable", "Renewable"],
                    ["auto_close", "Auto close"],
                  ].map(([key, label]) => (
                    <label className="check" key={key}>
                      <input
                        type="checkbox"
                        checked={form[key]}
                        onChange={(event) => setForm({ ...form, [key]: event.target.checked })}
                      />
                      {label}
                    </label>
                  ))}
                </div>
                <button className="btn btn-primary" disabled={busy}>Create plan</button>
              </form>
            </Card>
          )}
          <Card title="Plan catalog" subtitle={`${plans.length} plans`}>
            {plans.length === 0 ? (
              <Empty title="No plans yet">Create a product, then add a plan.</Empty>
            ) : (
              <Table>
                <thead>
                  <tr><th>Product</th><th>Price</th><th>Period</th><th>Availability</th><th>Rules</th></tr>
                </thead>
                <tbody>
                  {plans.map((plan) => (
                    <tr key={plan.id}>
                      <td><strong>{productName(plan.product)}</strong></td>
                      <td>{money(plan.price)}</td>
                      <td className="capitalize">{plan.period}</td>
                      <td>{date(plan.start_date)} → {date(plan.end_date)}</td>
                      <td className="flag-list">
                        {plan.pausable && <span>Pause</span>}
                        {plan.closable && <span>Close</span>}
                        {plan.renewable && <span>Renew</span>}
                        {plan.auto_close && <span>Auto close</span>}
                      </td>
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
