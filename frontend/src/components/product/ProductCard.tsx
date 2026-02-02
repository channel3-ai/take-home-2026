import { Link } from 'react-router-dom';
import type { Product } from '../../types/product';
import { getProductId, formatPrice } from '../../utils/product';
import { ProductImage } from './ProductImage';
import { ColorSwatches } from './ColorSwatches';

interface ProductCardProps {
  product: Product;
  index: number;
}

export const ProductCard = ({ product, index }: ProductCardProps) => {
  const productId = getProductId(product, index);
  
  // Get image from product level, or fall back to first color variant's images
  const getImageUrl = (): string => {
    if (product.image_urls && product.image_urls.length > 0) {
      return product.image_urls[0];
    }
    
    // Fall back to first color variant's first image
    const firstColorVariant = product.variants?.find(
      (v) => v.variant_type?.toLowerCase() === 'color' && 
             v.image_urls && 
             v.image_urls.length > 0
    );
    
    return firstColorVariant?.image_urls?.[0] || '';
  };
  
  const imageUrl = getImageUrl();

  return (
    <div>
      <Link
        to={`/products/${productId}`}
        className="group block no-underline animate-fade-in"
        style={{ 
          textDecoration: 'none',
          animationDelay: `${index * 50}ms`,
          animationFillMode: 'both'
        }}
      >
        <div>
          {/* Image Container */}
          <div className="relative w-full overflow-hidden bg-muted flex items-center justify-center" style={{ height: '400px', width: '100%' }}>
            <ProductImage src={imageUrl} alt={product.name} index={index} />
          </div>

          {/* Product Info */}
          <div className="mt-2 space-y-1.5 px-2 pb-2 text-center">
            {/* Color Swatches */}
            {product.colors && product.colors.length > 0 && (
              <ColorSwatches colors={product.colors} />
            )}

            {/* Product Name */}
            <div 
              className="text-base font-semibold text-black uppercase tracking-wide leading-tight"
              style={{ textDecoration: 'none', fontSize: '15px' }}
            >
              {product.name}
            </div>
            
            {/* Price */}
            <p 
              className="text-base font-semibold text-black"
              style={{ textDecoration: 'none', fontSize: '14px' }}
            >
              {formatPrice(product.price)}
            </p>
          </div>
        </div>
      </Link>
    </div>
  );
};
