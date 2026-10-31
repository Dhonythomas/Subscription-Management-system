import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { date, money, rows } from "../lib/format";
import { Card, Empty, ErrorBox, Field, Loading, PageHeader, Table } from "../components/ui";

const today = () => new Date().toISOString().slice(0, 10);
const nextYear = () => {
  const value = new Date();
  value.setFullYear(value.getFullYear() + 1);
  return value.toISOString().slice(0, 10);
};

function emptyForm() {
  return {
    name: "",
    type: "percent",
    value: "",
    min_amount: "",
    min_qty: "",
    scope: "subscription",
    products: [],
    start_date: today(),
    end_date: nextYear(),
    usage_limit: "100",
    is_active: true,
  };
}

export default function DiscountsPage() {
  const [discounts, setDiscounts] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [discountData, productData] = await Promise.all([
        api.get("/discounts/"),
        api.get("/catalog/products/"),
      ]);
      setDiscounts(rows(discountData));
      setProducts(rows(productData));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(load, []);

  function update(field) {
    return (event) => setForm({ ...form, [field]: event.target.value });
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/discounts/", {
        ...form,
        value: form.value,
        min_amount: form.min_amount || null,
        min_qty: form.min_qty || null,
        usage_limit: form.usage_limit ? Number(form.usage_limit) : null,
        products: form.scope === "product" ? form.products.map(Number) : [],
      });
      setForm(emptyForm());
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function toggle(discount) {
    setError(null);
    try {
      await api.patch(`/discounts/${discount.id}/`, { is_active: !discount.is_active });
      await load();
    } catch (err) {
      setError(err);
    }
  }

  const productNames = (ids) =>
    ids?.length
      ? ids.map((id) => products.find((product) => product.id === id)?.name || `#${id}`).join(", ")
      : "—";

  return (
    <>
      <PageHeader
        eyebrow="Discount engine"
        title="Discount rules"
        description="Discounts apply automatically during invoice generation and stop at their date or usage limit."
      />
      <ErrorBox error={error} onRetry={load} />
      {loading ? (
        <Loading />
      ) : (
        <>
          <Card title="New discount rule" subtitle="Admin-only. Percentage and fixed discounts are supported.">
            <form onSubmit={submit} className="stack">
              <div className="form-grid">
                <Field label="Name">
                  <input value={form.name} onChange={update("name")} required />
                </Field>
                <Field label="Type">
                  <select value={form.type} onChange={update("type")}>
                    <option value="percent">Percentage</option>
                    <option value="fixed">Fixed amount</option>
                  </select>
                </Field>
                <Field label={form.type === "percent" ? "Value (%)" : "Value"}>
                  <input type="number" step="0.01" min="0.01" value={form.value} onChange={update("value")} required />
                </Field>
                <Field label="Scope">
                  <select value={form.scope} onChange={update("scope")}>
                    <option value="subscription">Whole subscription</option>
                    <option value="product">Selected products</option>
                  </select>
                </Field>
                <Field label="Start date">
                  <input type="date" value={form.start_date} onChange={update("start_date")} required />
                </Field>
                <Field label="End date">
                  <input type="date" value={form.end_date} onChange={update("end_date")} required />
                </Field>
                <Field label="Minimum amount" hint="Optional">
                  <input type="number" step="0.01" min="0" value={form.min_amount} onChange={update("min_amount")} />
                </Field>
                <Field label="Minimum quantity" hint="Optional">
                  <input type="number" step="0.01" min="0" value={form.min_qty} onChange={update("min_qty")} />
                </Field>
                <Field label="Usage limit" hint="Optional; blank means unlimited.">
                  <input type="number" min="0" value={form.usage_limit} onChange={update("usage_limit")} />
                </Field>
              </div>
              {form.scope === "product" && (
                <Field label="Products">
                  <select
                    multiple
                    value={form.products}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        products: Array.from(event.target.selectedOptions, (option) => option.value),
                      })
                    }
                  >
                    {products.map((product) => (
                      <option key={product.id} value={product.id}>{product.name}</option>
                    ))}
                  </select>
                </Field>
              )}
              <button className="btn btn-primary" disabled={busy}>Create discount</button>
            </form>
          </Card>
          <Card title="Discount rules" subtitle={`${discounts.length} rules`}>
            {discounts.length === 0 ? (
              <Empty title="No discounts yet">Create a rule to apply it automatically on the next invoice.</Empty>
            ) : (
              <Table>
                <thead>
                  <tr><th>Name</th><th>Value</th><th>Scope</th><th>Window</th><th>Usage</th><th>Status</th><th>Action</th></tr>
                </thead>
                <tbody>
                  {discounts.map((discount) => (
                    <tr key={discount.id}>
                      <td><strong>{discount.name}</strong></td>
                      <td>{discount.type === "percent" ? `${Number(discount.value).toFixed(2)}%` : money(discount.value)}</td>
                      <td>
                        {discount.scope === "product" ? productNames(discount.products) : "Whole subscription"}
                      </td>
                      <td>{date(discount.start_date)} → {date(discount.end_date)}</td>
                      <td>{discount.used_count} / {discount.usage_limit ?? "∞"}</td>
                      <td>{discount.is_active ? "Active" : "Inactive"}</td>
                      <td>
                        <button type="button" className="btn btn-small btn-secondary" onClick={() => toggle(discount)}>
                          {discount.is_active ? "Deactivate" : "Activate"}
                        </button>
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
