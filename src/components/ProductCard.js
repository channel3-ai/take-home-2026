import { Link } from "react-router-dom";

export default function ProductCard({ product, index }) {
  const { name, brand, price } = product;

  return (
    <Link to={`/product/${index}`} className="card">
      <div className="card-body">
        <h3 className="card-title">{name}</h3>
        <p className="card-brand">{brand}</p>
        <p className="card-price">
          {price.currency} {price.price}
        </p>
      </div>
    </Link>
  );
}
