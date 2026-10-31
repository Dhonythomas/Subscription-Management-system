import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { date, money, rows } from "../lib/format";
import { Card, Empty, ErrorBox, Loading, Metric, PageHeader, Table } from "../components/ui";

export default function ReportsPage() {
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setMetrics(rows(await api.get("/reports/metrics/")));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(load, []);

  const latest = metrics[0];

  return (
    <>
      <PageHeader
        eyebrow="Reports"
        title="Daily finance history"
        description="The read model keeps one snapshot per day for fast dashboard queries."
      />
      <ErrorBox error={error} onRetry={load} />
      {loading ? (
        <Loading />
      ) : metrics.length === 0 ? (
        <Card>
          <Empty title="No snapshots yet">
            Run `python manage.py refresh_metrics` or open the Overview screen.
          </Empty>
        </Card>
      ) : (
        <>
          <div className="metric-grid">
            <Metric label="Snapshot" value={date(latest.date)} detail="Most recent read model" />
            <Metric label="MRR" value={money(latest.mrr)} detail={`ARR ${money(latest.arr)}`} tone="blue" />
            <Metric label="Outstanding" value={money(latest.outstanding)} detail={`${latest.overdue_invoices} overdue`} tone="amber" />
            <Metric label="Collected" value={money(latest.revenue_collected)} detail={date(latest.date)} tone="green" />
          </div>
          <Card title="Metric snapshots" subtitle={`${metrics.length} rows`}>
            <Table>
              <thead>
                <tr><th>Date</th><th>Active subscriptions</th><th>Revenue on day</th><th>Outstanding</th><th>Overdue</th><th>MRR</th><th>ARR</th></tr>
              </thead>
              <tbody>
                {metrics.map((row) => (
                  <tr key={row.id}>
                    <td><strong>{date(row.date)}</strong></td>
                    <td>{row.active_subscriptions}</td>
                    <td>{money(row.revenue_collected)}</td>
                    <td>{money(row.outstanding)}</td>
                    <td>{row.overdue_invoices}</td>
                    <td>{money(row.mrr)}</td>
                    <td>{money(row.arr)}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>
        </>
      )}
    </>
  );
}
