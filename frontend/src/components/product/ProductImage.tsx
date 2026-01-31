interface ProductImageProps {
  src: string;
  alt: string;
  index?: number;
  className?: string;
  style?: React.CSSProperties;
}

export const ProductImage = ({ 
  src, 
  alt, 
  index = 0,
  className = 'w-full h-full object-contain transition-transform duration-300 group-hover:scale-105',
  style
}: ProductImageProps) => {
  if (!src) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-muted text-muted-foreground" style={{ height: '400px' }}>
        <svg
          className="w-12 h-12 opacity-30"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      style={{ 
        width: '100%', 
        height: '100%', 
        objectFit: 'contain',
        objectPosition: 'center',
        ...style
      }}
      loading={index < 4 ? 'eager' : 'lazy'}
      onError={(e) => {
        const target = e.target as HTMLImageElement;
        target.style.display = 'none';
      }}
    />
  );
};
