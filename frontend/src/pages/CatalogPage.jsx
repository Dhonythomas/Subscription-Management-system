import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import { money, rows } from "../lib/format";
import { Card, Empty, ErrorBox, Field, Loading, PageHeader, Table } from "../components/ui";

const emptyProduct = {
  name: "",
  type: "service",
  sales_price: "",
  cost_price: "",
  notes: "",
};
const emptyTax = { name: "", rate: "" };
const emptyVariant = { product: "", attribute: "", value: "", price_delta: "" };

export default function CatalogPage() {
  const { user } = useAuth();
  const isAdmin = user.role === "admin";
  const [products, setProducts] = useState([]);
  const [variants, setVariants] = useState([]);
  const [taxes, setTaxes] = useState([]);
  const [productForm, setProductForm] = useState(emptyProduct);
  const [taxForm, setTaxForm] = useState(emptyTax);
  const [variantForm, setVariantForm] = useState(emptyVariant);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [productData, variantData, taxData] = await Promise.all([
        api.get("/catalog/products/"),
        api.get("/catalog/variants/"),
        api.get("/catalog/taxes/"),
      ]);
      setProducts(rows(productData));
      setVariants(rows(variantData));
      setTaxes(rows(taxData));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(load, []);

  async function create(path, payload, reset, setForm) {
    setBusy(true);
    setError(null);
    try {
      await api.post(path, payload);
      setForm(reset);
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const productName = (id) => products.find((product) => product.id === id)?.name || `#${id}`;

  return (
    <>
      <PageHeader
        eyebrow="Catalog"
        title="Products, variants, and taxes"
        description="The building blocks for plans and subscription lines. Admin writes; staff reads."
      />
      <ErrorBox error={error} onRetry={load} />
      {loading ? (
        <Loading />
      ) : (
        <>
          {isAdmin && (
            <div className="form-card-grid">
              <Card title="New product" subtitle="Money stays as decimal values.">
                <form
                  className="stack"
                  onSubmit={(event) => {
                    event.preventDefault();
                    create("/catalog/products/", productForm, emptyProduct, setProductForm);
                  }}
                >
                  <Field label="Name">
                    <input
                      value={productForm.name}
                      onChange={(event) => setProductForm({ ...productForm, name: event.target.value })}
                      required
                    />
                  </Field>
                  <div className="form-grid">
                    <Field label="Type">
                      <select
                        value={productForm.type}
                        onChange={(event) => setProductForm({ ...productForm, type: event.target.value })}
                      >
                        <option value="service">Service</option>
                        <option value="goods">Goods</option>
                      </select>
                    </Field>
                    <Field label="Sales price">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={productForm.sales_price}
                        onChange={(event) => setProductForm({ ...productForm, sales_price: event.target.value })}
                        required
                      />
                    </Field>
                    <Field label="Cost price">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={productForm.cost_price}
                        onChange={(event) => setProductForm({ ...productForm, cost_price: event.target.value })}
                        required
                      />
                    </Field>
                  </div>
                  <button className="btn btn-primary" disabled={busy}>Create product</button>
                </form>
              </Card>
              <Card title="New tax" subtitle="Percentage applied at invoice time.">
                <form
                  className="stack"
                  onSubmit={(event) => {
                    event.preventDefault();
                    create("/catalog/taxes/", taxForm, emptyTax, setTaxForm);
                  }}
                >
                  <Field label="Tax name">
                    <input
                      value={taxForm.name}
                      onChange={(event) => setTaxForm({ ...taxForm, name: event.target.value })}
                      required
                    />
                  </Field>
                  <Field label="Rate (%)" hint="Between 0 and 100.">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      value={taxForm.rate}
                      onChange={(event) => setTaxForm({ ...taxForm, rate: event.target.value })}
                      required
                    />
                  </Field>
                  <button className="btn btn-primary" disabled={busy}>Create tax</button>
                </form>
              </Card>
              <Card title="New variant" subtitle="Adds a price delta to a product.">
                <form
                  className="stack"
                  onSubmit={(event) => {
                    event.preventDefault();
                    create("/catalog/variants/", variantForm, emptyVariant, setVariantForm);
                  }}
                >
                  <Field label="Product">
                    <select
                      value={variantForm.product}
                      onChange={(event) => setVariantForm({ ...variantForm, product: event.target.value })}
                      required
                    >
                      <option value="">Select product</option>
                      {products.map((product) => (
                        <option key={product.id} value={product.id}>{product.name}</option>
                      ))}
                    </select>
                  </Field>
                  <div className="form-grid">
                    <Field label="Attribute">
                      <input
                        value={variantForm.attribute}
                        onChange={(event) => setVariantForm({ ...variantForm, attribute: event.target.value })}
                        required
                      />
                    </Field>
                    <Field label="Value">
                      <input
                        value={variantForm.value}
                        onChange={(event) => setVariantForm({ ...variantForm, value: event.target.value })}
                        required
                      />
                    </Field>
                  </div>
                  <Field label="Price delta">
                    <input
                      type="number"
                      step="0.01"
                      value={variantForm.price_delta}
                      onChange={(event) => setVariantForm({ ...variantForm, price_delta: event.target.value })}
                      required
                    />
                  </Field>
                  <button className="btn btn-primary" disabled={busy}>Create variant</button>
                </form>
              </Card>
            </div>
          )}

          <Card title="Products" subtitle={`${products.length} in catalog`}>
            {products.length === 0 ? (
              <Empty title="No products yet">Create one to start building plans.</Empty>
            ) : (
              <Table>
                <thead>
                  <tr><th>Name</th><th>Type</th><th>Sales</th><th>Cost</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {products.map((product) => (
                    <tr key={product.id}>
                      <td><strong>{product.name}</strong></td>
                      <td className="capitalize">{product.type}</td>
                      <td>{money(product.sales_price)}</td>
                      <td>{money(product.cost_price)}</td>
                      <td>{product.is_active ? "Active" : "Inactive"}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>

          <div className="split-grid">
            <Card title="Variants" subtitle={`${variants.length} configured`}>
              {variants.length === 0 ? (
                <Empty title="No variants" />
              ) : (
                <Table>
                  <thead><tr><th>Product</th><th>Attribute</th><th>Value</th><th>Delta</th></tr></thead>
                  <tbody>
                    {variants.map((variant) => (
                      <tr key={variant.id}>
                        <td>{productName(variant.product)}</td>
                        <td>{variant.attribute}</td>
                        <td>{variant.value}</td>
                        <td>{money(variant.price_delta)}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card>
            <Card title="Taxes" subtitle={`${taxes.length} configured`}>
              {taxes.length === 0 ? (
                <Empty title="No taxes" />
              ) : (
                <Table>
                  <thead><tr><th>Name</th><th>Rate</th><th>Status</th></tr></thead>
                  <tbody>
                    {taxes.map((tax) => (
                      <tr key={tax.id}>
                        <td><strong>{tax.name}</strong></td>
                        <td>{Number(tax.rate).toFixed(2)}%</td>
                        <td>{tax.is_active ? "Active" : "Inactive"}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card>
          </div>
        </>
      )}
    </>
  );
}
