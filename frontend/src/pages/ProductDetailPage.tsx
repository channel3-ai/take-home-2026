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
  const [failedImages, setFailedImages] = useState<Set<string>>(new Set());

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
        
        // Set default selected color variant if available (only if it has images)
        if (foundProduct.variants) {
          const colorVariant = foundProduct.variants.find(
            (v) => v.variant_type.toLowerCase() === 'color' &&
                   v.image_urls && 
                   v.image_urls.length > 0
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

  // Track failed images
  const handleImageFailed = (imageUrl: string) => {
    setFailedImages(prev => new Set([...prev, imageUrl]));
  };

  // Filter out color variants whose images all failed or have no images
  const filterVariantsWithFailedImages = (variants: Variant[]): Variant[] => {
    return variants.filter(variant => {
      // Only filter color variants
      if (variant.variant_type.toLowerCase() !== 'color') {
        return true;
      }
      // If color variant has no images, exclude it
      if (!variant.image_urls || variant.image_urls.length === 0) {
        return false;
      }
      // Check if all images for this variant have failed
      const allImagesFailed = variant.image_urls.every(url => failedImages.has(url));
      return !allImagesFailed;
    });
  };

  // Group variants by type and filter out variants with all failed images
  const groupedVariants = product?.variants?.reduce((acc, variant) => {
    if (!acc[variant.variant_type]) {
      acc[variant.variant_type] = [];
    }
    acc[variant.variant_type].push(variant);
    return acc;
  }, {} as Record<string, Variant[]>) || {};

  // Filter variants to remove colors with all failed images
  const filteredGroupedVariants = Object.entries(groupedVariants).reduce((acc, [variantType, variants]) => {
    acc[variantType] = filterVariantsWithFailedImages(variants);
    return acc;
  }, {} as Record<string, Variant[]>);

  // If selected color variant was filtered out, auto-select first available color
  useEffect(() => {
    if (product && selectedVariants.color) {
      const colorVariants = filteredGroupedVariants['color'] || [];
      const isSelectedColorValid = colorVariants.some(v => v.variant_value === selectedVariants.color);
      
      if (!isSelectedColorValid && colorVariants.length > 0) {
        // Selected color was filtered out, select first available color
        setSelectedVariants(prev => ({
          ...prev,
          color: colorVariants[0].variant_value,
        }));
      } else if (!isSelectedColorValid && colorVariants.length === 0) {
        // No color variants available, clear selection
        setSelectedVariants(prev => {
          const newVariants = { ...prev };
          delete newVariants.color;
          return newVariants;
        });
      }
    }
  }, [product, filteredGroupedVariants, selectedVariants.color]);

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
      <style>{`
        @keyframes fade-in {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @media (prefers-reduced-motion: reduce) {
          .animate-fade-in {
            animation: none;
          }
        }
        .animate-fade-in {
          animation: fade-in 0.4s ease-out;
        }
      `}</style>
      <div className="grid grid-cols-2 h-full">
        {/* Left Side - Images */}
        <div className="overflow-y-auto border-r border-border flex items-center justify-center animate-fade-in">
          <ProductImageGallery 
            images={images} 
            productName={product.name}
            onImageFailed={handleImageFailed}
          />
        </div>

        {/* Right Side - Product Details */}
        <div className="overflow-y-auto p-8 animate-fade-in" style={{ animationDelay: '100ms', animationFillMode: 'both' }}>
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
            {Object.keys(filteredGroupedVariants).length > 0 && (
              <div className="space-y-4">
                {Object.entries(filteredGroupedVariants).map(([variantType, variants]) => {
                  // If selected variant was filtered out, clear the selection
                  const selectedValue = selectedVariants[variantType];
                  const isValidSelection = variants.some(v => v.variant_value === selectedValue);
                  const displayValue = isValidSelection ? selectedValue : undefined;
                  
                  return (
                    <VariantSelector
                      key={variantType}
                      variantType={variantType}
                      variants={variants}
                      selectedValue={displayValue}
                      onSelect={handleVariantSelect}
                    />
                  );
                })}
              </div>
            )}

            {product.category && (
              <div className="space-y-2">
                <h2 className="text-xl font-semibold text-foreground">
                  Category
                </h2>
                <p className="text-foreground leading-relaxed">
                  {product.category.name}
                </p>
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
