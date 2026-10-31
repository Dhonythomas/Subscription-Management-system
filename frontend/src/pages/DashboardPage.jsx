import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { date, money } from "../lib/format";
import { Card, ErrorBox, Loading, Metric, PageHeader } from "../components/ui";

export default function DashboardPage() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    setError(null);
    api
      .get("/reports/dashboard/")
      .then(setMetrics)
      .catch(setError)
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  return (
    <>
      <PageHeader
        eyebrow="Finance overview"
        title="Good morning, Brightloop"
        description="A live snapshot of recurring revenue, collections, and overdue work."
      />
      {loading && <Loading label="Building your finance snapshot…" />}
      <ErrorBox error={error} onRetry={load} />
      {metrics && (
        <>
          <div className="metric-grid">
            <Metric
              label="Active subscriptions"
              value={metrics.active_subscriptions}
              detail="Currently billing"
              tone="teal"
            />
            <Metric
              label="MRR"
              value={money(metrics.mrr)}
              detail={`ARR ${money(metrics.arr)}`}
              tone="blue"
            />
            <Metric
              label="Collected today"
              value={money(metrics.revenue_collected)}
              detail={date(metrics.date)}
              tone="green"
            />
            <Metric
              label="Outstanding"
              value={money(metrics.outstanding)}
              detail={`${metrics.overdue_invoices} overdue invoice(s)`}
              tone={metrics.overdue_invoices ? "amber" : "default"}
            />
          </div>
          <div className="dashboard-grid">
            <Card title="Today's read" subtitle="Metrics refresh daily and on request.">
              <dl className="detail-list">
                <div><dt>Snapshot date</dt><dd>{date(metrics.date)}</dd></div>
                <div><dt>Recurring revenue</dt><dd>{money(metrics.mrr)}/mo</dd></div>
                <div><dt>Annual run rate</dt><dd>{money(metrics.arr)}</dd></div>
                <div><dt>Overdue invoices</dt><dd>{metrics.overdue_invoices}</dd></div>
              </dl>
            </Card>
            <Card title="What this screen proves" subtitle="Built for a fast, honest demo.">
              <ul className="check-list">
                <li>Invoice generation is idempotent: run billing twice, nothing duplicates.</li>
                <li>Every subscription transition writes an audit record and outbox event.</li>
                <li>Payments automatically mark invoices paid when the balance clears.</li>
                <li>Customer access is backend-scoped to their own records.</li>
              </ul>
            </Card>
          </div>
        </>
      )}
    </>
  );
}
