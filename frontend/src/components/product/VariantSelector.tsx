import type { Variant } from '../../types/product';
import { getColorValue } from '../../utils/colors';

interface VariantSelectorProps {
  variantType: string;
  variants: Variant[];
  selectedValue?: string;
  onSelect: (variantType: string, variantValue: string) => void;
}

export const VariantSelector = ({ 
  variantType, 
  variants, 
  selectedValue,
  onSelect 
}: VariantSelectorProps) => {
  const isColorVariant = variantType.toLowerCase() === 'color';

  return (
    <div className="space-y-4">
      {isColorVariant ? (
        <div className="space-y-2">
          {/* Label showing selected color */}
          <div className="flex items-center gap-2">
            <span className="font-semibold text-foreground capitalize">
              {variantType}
            </span>
            <span className="font-normal text-foreground">
              {selectedValue || variants[0]?.variant_value || ''}
            </span>
          </div>
          {/* Color swatches - show images if available, otherwise show color */}
          <div className="flex flex-wrap gap-2">
            {variants.map((variant, index) => {
              const isSelected = selectedValue === variant.variant_value;
              const hasImages = variant.image_urls && variant.image_urls.length > 0;
              const imageUrl = hasImages ? variant.image_urls[0] : null;
              
              return (
                <button
                  key={index}
                  onClick={() => onSelect(variantType, variant.variant_value)}
                  className="p-0 border-0 bg-transparent cursor-pointer focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-foreground rounded overflow-hidden"
                  aria-label={`Select ${variant.variant_value}`}
                >
                  <div
                    className={`w-12 h-12 border-2 transition-all ${
                      isSelected
                        ? 'border-black border-[3px]'
                        : 'border-border hover:border-foreground/50'
                    }`}
                    style={
                      imageUrl
                        ? {
                            backgroundImage: `url(${imageUrl})`,
                            backgroundSize: 'cover',
                            backgroundPosition: 'center',
                            backgroundColor: getColorValue(variant.variant_value), // Fallback color
                          }
                        : {
                            backgroundColor: getColorValue(variant.variant_value),
                          }
                    }
                  >
                    {imageUrl && (
                      <img
                        src={imageUrl}
                        alt={variant.variant_value}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          // If image fails to load, hide it and show color background
                          const target = e.target as HTMLImageElement;
                          target.style.display = 'none';
                        }}
                      />
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <>
          <h3 className="text-lg font-semibold text-foreground capitalize">
            {variantType}
          </h3>
          <div className="flex flex-wrap gap-2">
            {variants.map((variant, index) => {
              const isSelected = selectedValue === variant.variant_value;
              return (
                <button
                  key={index}
                  onClick={() => onSelect(variantType, variant.variant_value)}
                  className={`px-4 py-2 border-2 rounded transition-colors ${
                    isSelected
                      ? 'border-foreground bg-foreground text-background'
                      : 'border-border hover:border-foreground/50'
                  }`}
                >
                  {variant.variant_value}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};
