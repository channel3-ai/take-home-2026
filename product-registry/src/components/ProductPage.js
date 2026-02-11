import { useState } from "react";
import { useParams, Link } from "react-router-dom";

export default function ProductPage({ products }) {
  const { id } = useParams();
  const product = products[id];

  const [activeVariant, setActiveVariant] = useState(null);

  if (!product) return <p>Not found.</p>;

  const { name, brand, description, key_features, price, colors, variants } =
    product;

  const images =
    activeVariant?.image_urls?.length > 0
      ? activeVariant?.image_urls
      : product?.image_urls;

  const video = activeVariant?.video_url || product.video_url;

  return (
    <div className="product-page">
      <Link to="/" className="back-link">
        ← Back to catalog
      </Link>

      <h1 className="product-title">{name}</h1>
      <p className="product-brand">{brand}</p>

      {/* MEDIA */}
      <div className="media">
        {video ? (
          <video controls className="video">
            <source src={video} />
          </video>
        ) : images?.length > 0 ? (
          <img src={images[0]} alt={name} className="image" />
        ) : (
          <div className="image placeholder">No media available.</div>
        )}
      </div>

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
          <h2>Key Features</h2>
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
          <div className="variants">
            {variants.map((v, i) => (
              <button key={i} onClick={() => setActiveVariant(v)}>
                {v.key}: {v.value}
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
