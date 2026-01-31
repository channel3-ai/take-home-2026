import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import type { Product, Variant } from '../types/product';
import { API_BASE } from '../utils/api';
import { formatPrice, getProductId } from '../utils/product';
import { BackButton } from '../components/ui/BackButton';
import { ProductImageGallery } from '../components/product/ProductImageGallery';
import { VariantSelector } from '../components/product/VariantSelector';

const ProductDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVariants, setSelectedVariants] = useState<Record<string, string>>({});

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`${API_BASE}/products`);

        if (!response.ok) {
          throw new Error(`Failed to fetch products: ${response.statusText}`);
        }

        const products: Product[] = await response.json();
        const foundProduct = products.find(p => getProductId(p) === id);

        if (!foundProduct) {
          throw new Error('Product not found');
        }

        setProduct(foundProduct);
        
        // Set default selected color variant if available
        if (foundProduct.variants) {
          const colorVariant = foundProduct.variants.find(
            (v) => v.variant_type.toLowerCase() === 'color'
          );
          if (colorVariant) {
            setSelectedVariants(prev => ({
              ...prev,
              color: colorVariant.variant_value,
            }));
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load product');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchProduct();
    }
  }, [id]);

  // Group variants by type
  const groupedVariants = product?.variants?.reduce((acc, variant) => {
    if (!acc[variant.variant_type]) {
      acc[variant.variant_type] = [];
    }
    acc[variant.variant_type].push(variant);
    return acc;
  }, {} as Record<string, Variant[]>) || {};

  const handleVariantSelect = (variantType: string, variantValue: string) => {
    setSelectedVariants(prev => ({
      ...prev,
      [variantType]: variantValue,
    }));
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-medium text-foreground mb-4">
            {error || 'Product not found'}
          </p>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
          >
            Back to Products
          </button>
        </div>
      </div>
    );
  }

  // Get images based on selected color variant
  const getDisplayImages = (): string[] => {
    // Check if a color variant is selected and has images
    const selectedColorVariant = product.variants?.find(
      (v) => v.variant_type.toLowerCase() === 'color' && 
             v.variant_value === selectedVariants.color &&
             v.image_urls && 
             v.image_urls.length > 0
    );
    
    // Debug logging
    if (selectedVariants.color) {
      console.log('Selected color:', selectedVariants.color);
      console.log('Found variant:', selectedColorVariant ? selectedColorVariant.variant_value : 'none');
      console.log('Variant images:', selectedColorVariant?.image_urls?.length || 0);
    }
    
    // If selected color variant has images, use those; otherwise use product images
    return selectedColorVariant?.image_urls || product.image_urls || [];
  };

  const images = getDisplayImages();

  return (
    <div className="h-screen overflow-hidden">
      <div className="grid grid-cols-2 h-full">
        {/* Left Side - Images */}
        <div className="overflow-y-auto border-r border-border flex items-center justify-center" >
          <ProductImageGallery images={images} productName={product.name} />
        </div>

        {/* Right Side - Product Details */}
        <div className="overflow-y-auto p-8">
          <div className="max-w-2xl mx-auto space-y-6">
            <BackButton />

            <h1 className="text-3xl font-bold text-foreground">
              {product.name}
            </h1>

            {product.brand && (
              <p className="text-lg text-muted-foreground">
                {product.brand}
              </p>
            )}

            <p className="text-2xl font-semibold text-foreground">
              {formatPrice(product.price)}
            </p>

            {/* Variants Section */}
            {Object.keys(groupedVariants).length > 0 && (
              <div className="space-y-4">
                {Object.entries(groupedVariants).map(([variantType, variants]) => (
                  <VariantSelector
                    key={variantType}
                    variantType={variantType}
                    variants={variants}
                    selectedValue={selectedVariants[variantType]}
                    onSelect={handleVariantSelect}
                  />
                ))}
              </div>
            )}

            {product.description && (
              <div className="space-y-2">
                <h2 className="text-xl font-semibold text-foreground">
                  Description
                </h2>
                <p className="text-foreground leading-relaxed whitespace-pre-line">
                  {product.description}
                </p>
              </div>
            )}

            {product.key_features && product.key_features.length > 0 && (
              <div className="space-y-2">
                <h2 className="text-xl font-semibold text-foreground">
                  Features
                </h2>
                <ul className="space-y-2">
                  {product.key_features.map((feature, index) => (
                    <li key={index} className="text-foreground">
                      • {feature}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductDetailPage;
