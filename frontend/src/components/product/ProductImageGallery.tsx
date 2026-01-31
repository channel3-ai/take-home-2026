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

  return (
    <div className="p-8 space-y-6">
      {images.map((imageUrl, index) => (
        <div key={index} className="flex justify-center">
          <img
            src={imageUrl}
            alt={`${productName} - Image ${index + 1}`}
            className="max-w-full h-auto object-contain"
            loading={index < 2 ? 'eager' : 'lazy'}
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
            }}
          />
        </div>
      ))}
    </div>
  );
};
