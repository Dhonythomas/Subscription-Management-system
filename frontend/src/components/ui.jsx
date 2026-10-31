import { title } from "../lib/format";

export function PageHeader({ eyebrow, title: heading, description, actions }) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{heading}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

export function Card({ title: heading, subtitle, actions, children, className = "" }) {
  return (
    <section className={`card ${className}`}>
      {(heading || actions) && (
        <div className="card-head">
          <div>
            {heading && <h2>{heading}</h2>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}

export function Loading({ label = "Loading…" }) {
  return (
    <div className="loading">
      <span className="spinner" />
      {label}
    </div>
  );
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="error-box" role="alert">
      <span>{error.message || String(error)}</span>
      {onRetry && (
        <button type="button" className="btn btn-quiet" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Empty({ title: heading, children }) {
  return (
    <div className="empty">
      <strong>{heading}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}

export function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{title(status)}</span>;
}

export function Metric({ label, value, detail, tone = "default" }) {
  return (
    <div className={`metric metric-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </div>
  );
}

export function Table({ children }) {
  return (
    <div className="table-wrap">
      <table>{children}</table>
    </div>
  );
}
