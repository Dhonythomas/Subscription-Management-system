import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { date, money, rows, title } from "../lib/format";
import { Card, Empty, ErrorBox, Field, Loading, PageHeader, Table } from "../components/ui";

const today = () => new Date().toISOString().slice(0, 10);

export default function PaymentsPage() {
  const [payments, setPayments] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [form, setForm] = useState({
    invoice: "",
    method: "bank",
    amount: "",
    paid_on: today(),
    note: "",
  });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [paymentData, invoiceData] = await Promise.all([
        api.get("/payments/"),
        api.get("/billing/invoices/"),
      ]);
      setPayments(rows(paymentData));
      setInvoices(rows(invoiceData));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(load, []);

  function chooseInvoice(invoiceId) {
    const invoice = invoices.find((item) => String(item.id) === String(invoiceId));
    setForm({
      ...form,
      invoice: invoiceId,
      amount: invoice?.total || form.amount,
    });
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/payments/", {
        ...form,
        invoice: Number(form.invoice),
      });
      setForm({ invoice: "", method: "bank", amount: "", paid_on: today(), note: "" });
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const confirmedInvoices = invoices.filter((invoice) => invoice.status === "confirmed");

  return (
    <>
      <PageHeader
        eyebrow="Payments"
        title="Record money received"
        description="Payments apply against confirmed invoices. Clearing the balance marks the invoice Paid automatically."
      />
      <ErrorBox error={error} onRetry={load} />
      {loading ? (
        <Loading />
      ) : (
        <>
          <Card title="New payment" subtitle="Partial payments are supported; overpayments are rejected.">
            <form onSubmit={submit} className="stack">
              <div className="form-grid">
                <Field label="Confirmed invoice">
                  <select
                    value={form.invoice}
                    onChange={(event) => chooseInvoice(event.target.value)}
                    required
                  >
                    <option value="">Select invoice</option>
                    {confirmedInvoices.map((invoice) => (
                      <option key={invoice.id} value={invoice.id}>
                        {invoice.number} · {money(invoice.total)}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Method">
                  <select
                    value={form.method}
                    onChange={(event) => setForm({ ...form, method: event.target.value })}
                  >
                    <option value="bank">Bank transfer</option>
                    <option value="cash">Cash</option>
                    <option value="card">Card</option>
                    <option value="other">Other</option>
                  </select>
                </Field>
                <Field label="Amount">
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={form.amount}
                    onChange={(event) => setForm({ ...form, amount: event.target.value })}
                    required
                  />
                </Field>
                <Field label="Paid on">
                  <input
                    type="date"
                    value={form.paid_on}
                    onChange={(event) => setForm({ ...form, paid_on: event.target.value })}
                    required
                  />
                </Field>
                <Field label="Note">
                  <input
                    value={form.note}
                    onChange={(event) => setForm({ ...form, note: event.target.value })}
                  />
                </Field>
              </div>
              <button className="btn btn-primary" disabled={busy || !confirmedInvoices.length}>
                Record payment
              </button>
              {!confirmedInvoices.length && (
                <p className="muted">Confirm a draft invoice before recording a payment.</p>
              )}
            </form>
          </Card>
          <Card title="Payment history" subtitle={`${payments.length} payments`}>
            {payments.length === 0 ? (
              <Empty title="No payments yet" />
            ) : (
              <Table>
                <thead><tr><th>Payment</th><th>Invoice</th><th>Method</th><th>Amount</th><th>Paid on</th><th>Note</th></tr></thead>
                <tbody>
                  {payments.map((payment) => (
                    <tr key={payment.id}>
                      <td>Payment #{payment.id}</td>
                      <td>Invoice #{payment.invoice}</td>
                      <td>{title(payment.method)}</td>
                      <td><strong>{money(payment.amount)}</strong></td>
                      <td>{date(payment.paid_on)}</td>
                      <td className="muted">{payment.note || "—"}</td>
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
