import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import { date, money, rows } from "../lib/format";
import { Card, Empty, ErrorBox, Field, Loading, PageHeader, StatusBadge, Table } from "../components/ui";

const today = () => new Date().toISOString().slice(0, 10);
const nextYear = () => {
  const value = new Date();
  value.setFullYear(value.getFullYear() + 1);
  return value.toISOString().slice(0, 10);
};
const nextNumber = () => `SUB-${Date.now().toString().slice(-7)}`;

function initialForm() {
  return {
    number: nextNumber(),
    customer: "",
    plan: "",
    start_date: today(),
    expiry_date: nextYear(),
    payment_terms: "Net 30",
    product: "",
    qty: "1",
    unit_price: "",
    amount: "",
  };
}

const actionsByStatus = {
  draft: [["quotation", "Send quotation"]],
  quotation: [["confirm", "Confirm"]],
  confirmed: [["activate", "Activate"]],
  active: [["pause", "Pause"], ["close", "Close"]],
  paused: [["activate", "Resume"]],
  closed: [["renew", "Renew"]],
};

export default function SubscriptionsPage() {
  const { user } = useAuth();
  const canManage = ["admin", "staff"].includes(user.role);
  const [subscriptions, setSubscriptions] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [actionBusy, setActionBusy] = useState("");
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const subscriptionData = await api.get("/subscriptions/");
      setSubscriptions(rows(subscriptionData));
      if (canManage) {
        const [customerData, planData, productData] = await Promise.all([
          api.get("/accounts/customers/"),
          api.get("/plans/"),
          api.get("/catalog/products/"),
        ]);
        setCustomers(rows(customerData));
        setPlans(rows(planData));
        setProducts(rows(productData));
      }
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [canManage]);

  function choosePlan(planId) {
    const plan = plans.find((item) => String(item.id) === String(planId));
    setForm({
      ...form,
      plan: planId,
      product: plan?.product || form.product,
      unit_price: plan?.price || form.unit_price,
      amount: plan?.price || form.amount,
    });
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = {
        number: form.number,
        customer: Number(form.customer),
        plan: Number(form.plan),
        start_date: form.start_date,
        expiry_date: form.expiry_date,
        payment_terms: form.payment_terms,
        lines: [
          {
            product: Number(form.product),
            qty: form.qty,
            unit_price: form.unit_price,
            amount: form.amount,
          },
        ],
      };
      await api.post("/subscriptions/", payload);
      setForm(initialForm());
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function act(subscription, action) {
    setActionBusy(`${subscription.id}:${action}`);
    setError(null);
    try {
      await api.post(`/subscriptions/${subscription.id}/${action}/`, {});
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setActionBusy("");
    }
  }

  const planName = (id) => {
    const plan = plans.find((item) => item.id === id);
    return plan ? `${plan.period} · ${money(plan.price)}` : `Plan #${id}`;
  };

  return (
    <>
      <PageHeader
        eyebrow={canManage ? "Operations" : "Customer portal"}
        title={canManage ? "Subscriptions" : "My subscriptions"}
        description={
          canManage
            ? "Create subscriptions and move them through quotation, confirmation, activation, pause, close, and renewal."
            : "Your active and past subscriptions, with invoice access in the next tab."
        }
      />
      <ErrorBox error={error} onRetry={load} />
      {loading ? (
        <Loading />
      ) : (
        <>
          {canManage && (
            <Card title="New subscription" subtitle="Starts in Draft. Status only changes through actions.">
              <form onSubmit={submit} className="stack">
                <div className="form-grid">
                  <Field label="Subscription number">
                    <input
                      value={form.number}
                      onChange={(event) => setForm({ ...form, number: event.target.value })}
                      required
                    />
                  </Field>
                  <Field label="Customer">
                    <select
                      value={form.customer}
                      onChange={(event) => setForm({ ...form, customer: event.target.value })}
                      required
                    >
                      <option value="">Select customer</option>
                      {customers.map((customer) => (
                        <option key={customer.id} value={customer.id}>{customer.name}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Plan">
                    <select value={form.plan} onChange={(event) => choosePlan(event.target.value)} required>
                      <option value="">Select plan</option>
                      {plans.map((plan) => (
                        <option key={plan.id} value={plan.id}>
                          #{plan.id} · {plan.period} · {money(plan.price)}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Payment terms">
                    <input
                      value={form.payment_terms}
                      onChange={(event) => setForm({ ...form, payment_terms: event.target.value })}
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
                  <Field label="Expiry date">
                    <input
                      type="date"
                      value={form.expiry_date}
                      onChange={(event) => setForm({ ...form, expiry_date: event.target.value })}
                      required
                    />
                  </Field>
                </div>
                <div className="form-subhead">First subscription line</div>
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
                  <Field label="Quantity">
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={form.qty}
                      onChange={(event) => setForm({ ...form, qty: event.target.value })}
                      required
                    />
                  </Field>
                  <Field label="Unit price">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={form.unit_price}
                      onChange={(event) => setForm({ ...form, unit_price: event.target.value })}
                      required
                    />
                  </Field>
                  <Field label="Line amount">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={form.amount}
                      onChange={(event) => setForm({ ...form, amount: event.target.value })}
                      required
                    />
                  </Field>
                </div>
                <button className="btn btn-primary" disabled={busy}>Create subscription</button>
              </form>
            </Card>
          )}
          <Card title={canManage ? "All subscriptions" : "Your subscriptions"} subtitle={`${subscriptions.length} records`}>
            {subscriptions.length === 0 ? (
              <Empty title="No subscriptions yet" />
            ) : (
              <Table>
                <thead>
                  <tr>
                    <th>Number</th><th>Customer</th><th>Plan</th><th>Period</th>
                    <th>Status</th><th>Next billing</th><th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {subscriptions.map((subscription) => (
                    <tr key={subscription.id}>
                      <td><strong>{subscription.number}</strong></td>
                      <td>Customer #{subscription.customer}</td>
                      <td>{planName(subscription.plan)}</td>
                      <td>{date(subscription.start_date)} → {date(subscription.expiry_date)}</td>
                      <td><StatusBadge status={subscription.status} /></td>
                      <td>{date(subscription.next_billing_date)}</td>
                      <td>
                        {canManage ? (
                          <div className="action-row">
                            {(actionsByStatus[subscription.status] || []).map(([action, label]) => (
                              <button
                                key={action}
                                type="button"
                                className="btn btn-small btn-secondary"
                                disabled={actionBusy === `${subscription.id}:${action}`}
                                onClick={() => act(subscription, action)}
                              >
                                {actionBusy === `${subscription.id}:${action}` ? "…" : label}
                              </button>
                            ))}
                          </div>
                        ) : (
                          <span className="muted">Read only</span>
                        )}
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
