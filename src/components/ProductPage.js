import { useParams, Link } from "react-router-dom";

export default function ProductPage({ products }) {
  const { id } = useParams();
  const product = products[id];

  if (!product) return <p>Not found.</p>;

  const { name, brand, description, key_features, price, colors, variants } =
    product;

  return (
    <div className="product-page">
      <Link to="/" className="back-link">
        ← Back to catalog
      </Link>

      <h1 className="product-title">{name}</h1>
      <p className="product-brand">{brand}</p>

      <div className="price-block">
        <span className="price">
          {price.currency} {price.price}
        </span>
        {price.compare_at_price && (
          <span className="compare">
            {price.currency} {price.compare_at_price}
          </span>
        )}
      </div>

      <section>
        <h2>Overview</h2>
        <p>{description}</p>
      </section>

      {key_features?.length > 0 && (
        <section>
          <h2>Key features</h2>
          <ul>
            {key_features.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </section>
      )}

      {colors?.length > 0 && (
        <section>
          <h2>Colors</h2>
          <p>{colors.join(", ")}</p>
        </section>
      )}

      {variants?.length > 0 && (
        <section>
          <h2>Variants</h2>
          <ul>
            {variants.map((v, i) => (
              <li key={i}>
                {v.key}: {v.value}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
