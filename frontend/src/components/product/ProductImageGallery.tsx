interface ProductImageGalleryProps {
  images: string[];
  productName: string;
}

export const ProductImageGallery = ({ images, productName }: ProductImageGalleryProps) => {
  if (images.length === 0) {
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
    // For Nike images with size parameters
    if (url.includes('w_') || url.includes('h_')) {
      return url.replace(/w_\d+/g, 'w_2000').replace(/h_\d+/g, 'h_2000');
    }
    // For other CDN images, keep original URL (don't modify)
    return url;
  };
  
  return (
    <div className="w-full p-6 space-y-6" >
      {images.map((imageUrl, index) => {
              const highResUrl = getHighResImageUrl(imageUrl);
        return (
          <div key={index} className="flex justify-center items-center w-full min-h-[85vh]">
            <img
              src={highResUrl}
              alt={`${productName} - Image ${index + 1}`}
              className="max-w-full max-h-[90vh] w-auto h-auto object-contain"
              style={{
                imageRendering: 'auto',
              }}
              loading={index < 2 ? 'eager' : 'lazy'}
              decoding="async"
              onError={(e) => {
                console.error(`Failed to load image: ${imageUrl}`, e);
                const target = e.target as HTMLImageElement;
                // Don't hide the image, show a placeholder instead
                target.style.display = 'block';
                target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="400"%3E%3Crect width="400" height="400" fill="%23f0f0f0"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%23999"%3EImage not available%3C/text%3E%3C/svg%3E';
              }}
            />
          </div>
      );
    })}
    </div>
  );
};
