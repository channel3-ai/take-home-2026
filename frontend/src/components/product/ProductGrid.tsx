import type { Product } from '../../types/product';
import { getProductId } from '../../utils/product';
import { ProductCard } from './ProductCard';
import { EmptyState } from '../ui/EmptyState';

interface ProductGridProps {
  products: Product[];
}

export const ProductGrid = ({ products }: ProductGridProps) => {
  if (products.length === 0) {
    return <EmptyState />;
  }

  return (
    <div 
      className="grid gap-8 justify-items-center mx-auto w-full"
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
      }}
    >
      {products.map((product, index) => (
        <ProductCard key={getProductId(product, index)} product={product} index={index} />
      ))}
    </div>
  );
};
