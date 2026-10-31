import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { api, downloadPdf } from "../lib/api";
import { date, money, rows } from "../lib/format";
import { Card, Empty, ErrorBox, Loading, PageHeader, StatusBadge, Table } from "../components/ui";

export default function InvoicesPage() {
  const { user } = useAuth();
  const canManage = ["admin", "staff"].includes(user.role);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setInvoices(rows(await api.get("/billing/invoices/")));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(load, []);

  async function act(invoice, action) {
    setBusy(`${invoice.id}:${action}`);
    setError(null);
    try {
      await api.post(`/billing/invoices/${invoice.id}/${action}/`, {});
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy("");
    }
  }

  async function download(invoice) {
    setBusy(`${invoice.id}:pdf`);
    setError(null);
    try {
      await downloadPdf(`/billing/invoices/${invoice.id}/pdf/`, `${invoice.number}.pdf`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow={canManage ? "Billing" : "Customer portal"}
        title={canManage ? "Invoices" : "My invoices"}
        description="Every invoice is a snapshot. Download the PDF or move unpaid invoices through confirmation and cancellation."
      />
      <ErrorBox error={error} onRetry={load} />
      {loading ? (
        <Loading />
      ) : (
        <Card title={canManage ? "Invoice ledger" : "Your invoice history"} subtitle={`${invoices.length} invoices`}>
          {invoices.length === 0 ? (
            <Empty title="No invoices yet">Run billing to generate the first invoice.</Empty>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Invoice</th><th>Customer</th><th>Period</th><th>Total</th>
                  <th>Due</th><th>Status</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice) => (
                  <tr key={invoice.id}>
                    <td><strong>{invoice.number}</strong><small>{invoice.lines.length} line(s)</small></td>
                    <td>Customer #{invoice.customer}</td>
                    <td>{date(invoice.period_start)} → {date(invoice.period_end)}</td>
                    <td><strong>{money(invoice.total)}</strong></td>
                    <td>{date(invoice.due_date)}</td>
                    <td><StatusBadge status={invoice.status} /></td>
                    <td>
                      <div className="action-row">
                        <button
                          type="button"
                          className="btn btn-small btn-secondary"
                          disabled={busy === `${invoice.id}:pdf`}
                          onClick={() => download(invoice)}
                        >
                          {busy === `${invoice.id}:pdf` ? "…" : "PDF"}
                        </button>
                        {canManage && invoice.status === "draft" && (
                          <button
                            type="button"
                            className="btn btn-small btn-secondary"
                            disabled={busy === `${invoice.id}:confirm`}
                            onClick={() => act(invoice, "confirm")}
                          >
                            Confirm
                          </button>
                        )}
                        {canManage && ["draft", "confirmed"].includes(invoice.status) && (
                          <button
                            type="button"
                            className="btn btn-small btn-danger"
                            disabled={busy === `${invoice.id}:cancel`}
                            onClick={() => act(invoice, "cancel")}
                          >
                            Cancel
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      )}
    </>
  );
}
