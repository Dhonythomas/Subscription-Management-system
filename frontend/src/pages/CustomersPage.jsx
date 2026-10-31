import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { date, rows } from "../lib/format";
import { Card, Empty, ErrorBox, Loading, PageHeader, Table } from "../components/ui";

export default function CustomersPage() {
  const [customers, setCustomers] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setCustomers(rows(await api.get("/accounts/customers/")));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(load, []);

  const filtered = customers.filter((customer) => {
    const haystack = `${customer.name} ${customer.user?.email || ""} ${customer.billing_email}`.toLowerCase();
    return haystack.includes(query.toLowerCase());
  });

  return (
    <>
      <PageHeader
        eyebrow="Accounts"
        title="Customers"
        description="Customer records and billing contacts. Customer-scoped APIs prevent cross-account reads."
      />
      <ErrorBox error={error} onRetry={load} />
      {loading ? (
        <Loading />
      ) : (
        <Card
          title="Customer directory"
          subtitle={`${filtered.length} of ${customers.length} customers`}
          actions={
            <input
              className="compact-input"
              placeholder="Search name or email"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          }
        >
          {customers.length === 0 ? (
            <Empty title="No customers yet">Customers appear here after self-registration.</Empty>
          ) : (
            <Table>
              <thead><tr><th>Customer</th><th>Login email</th><th>Billing email</th><th>Phone</th><th>Since</th></tr></thead>
              <tbody>
                {filtered.map((customer) => (
                  <tr key={customer.id}>
                    <td><strong>{customer.name}</strong><small>Customer #{customer.id}</small></td>
                    <td>{customer.user?.email || "—"}</td>
                    <td>{customer.billing_email || "—"}</td>
                    <td>{customer.billing_phone || "—"}</td>
                    <td>{date(customer.created_at?.slice(0, 10))}</td>
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
