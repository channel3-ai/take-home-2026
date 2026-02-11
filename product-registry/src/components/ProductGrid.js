import ProductCard from "./ProductCard";

export default function ProductGrid({ products }) {
  return (
    <div className="grid">
      {products.map((p, i) => (
        <ProductCard key={i} product={p} index={i} />
      ))}
    </div>
  );
}
