import { useState, type SyntheticEvent } from 'react';

interface ProductImageGalleryProps {
  images: string[];
  productName: string;
  onImageFailed?: (imageUrl: string) => void;
}

export const ProductImageGallery = ({ images, productName, onImageFailed }: ProductImageGalleryProps) => {
  const [failedImages, setFailedImages] = useState<Set<string>>(new Set());

  // Filter out images that have failed to load
  const validImages = images.filter(url => !failedImages.has(url));

  if (validImages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        No images available
      </div>
    );
  }
  const getHighResImageUrl = (url: string): string => {
    // For Article CDN images - keep original URL (already high res with w=3840)
    if (url.includes('cdn-images.article.com')) {
      return url; // Article URLs already have w=3840, keep as-is
    }
    // For LL Bean images with size parameters
    if (url.includes('hei=') && url.includes('wid=')) {
      return url
        .replace(/hei=\d+/g, 'hei=2000')
        .replace(/wid=\d+/g, 'wid=2000');
    }
    // For Nike images - DON'T modify them
    // Nike CDN handles resolution automatically based on template (t_default, t_PDP_144_v1, etc.)
    // The w_1.0 and h_1.0 are scale factors, not pixel dimensions
    if (url.includes('static.nike.com')) {
      return url; // Keep original - Nike CDN handles resolution
    }
    // For other CDN images, keep original URL (don't modify)
    return url;
  };

  const handleImageError = (
    index: number,
    originalUrl: string,
    highResUrl: string,
    e: SyntheticEvent<HTMLImageElement>
  ) => {
    const target = e.target as HTMLImageElement;
    const retryCount = parseInt(target.dataset.retryCount || '0');
    const originalUrlAttr = target.dataset.originalUrl || originalUrl;
    
    // First retry: try original URL if we modified it
    if (retryCount === 0 && highResUrl !== originalUrlAttr) {
      console.log(`Retrying image ${index} with original URL (attempt 1):`, originalUrlAttr);
      target.dataset.retryCount = '1';
      target.dataset.originalUrl = originalUrlAttr;
      target.src = originalUrlAttr;
      return;
    }
    
    // Second retry: wait and try high-res URL again (in case of temporary network issue)
    if (retryCount === 1) {
      console.log(`Retrying image ${index} with high-res URL (attempt 2):`, highResUrl);
      setTimeout(() => {
        target.dataset.retryCount = '2';
        target.src = highResUrl;
      }, 1000);
      return;
    }
    
    // Third retry: try original URL one more time
    if (retryCount === 2 && highResUrl !== originalUrlAttr) {
      console.log(`Retrying image ${index} with original URL (attempt 3):`, originalUrlAttr);
      setTimeout(() => {
        target.dataset.retryCount = '3';
        target.src = originalUrlAttr;
      }, 2000);
      return;
    }
    
    // All retries failed - mark this image as failed and remove it from display
    console.error(`Failed to load image after ${retryCount + 1} attempts:`, originalUrlAttr);
    setFailedImages(prev => {
      const newSet = new Set([...prev, originalUrlAttr]);
      // Notify parent component about failed image
      if (onImageFailed) {
        onImageFailed(originalUrlAttr);
      }
      return newSet;
    });
    // Hide the image element
    if (target.parentElement) {
      target.parentElement.style.display = 'none';
    }
  };
  
  return (
    <div className="w-full p-6 space-y-6">
      {validImages.map((imageUrl, index) => {
        const highResUrl = getHighResImageUrl(imageUrl);
        return (
          <div key={`${imageUrl}-${index}`} className="flex justify-center items-center w-full min-h-[85vh]">
            <img
              src={highResUrl}
              data-retry-count="0"
              data-original-url={imageUrl}
              alt={`${productName} - Image ${index + 1}`}
              className="w-full max-w-xl mx-auto"
              style={{
                imageRendering: 'auto',
              }}
              loading={index < 2 ? 'eager' : 'lazy'}
              decoding="async"
              onError={(e) => handleImageError(index, imageUrl, highResUrl, e)}
            />
          </div>
        );
      })}
    </div>
  );
};
