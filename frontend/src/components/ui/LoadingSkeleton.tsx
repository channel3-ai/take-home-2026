interface LoadingSkeletonProps {
  count?: number;
}

export const LoadingSkeleton = ({ count = 8 }: LoadingSkeletonProps) => {
  return (
    <div className="grid grid-cols-3 gap-8 justify-items-center">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="animate-pulse">
          <div className="aspect-square bg-muted rounded mb-3" />
          <div className="h-4 bg-muted rounded mb-2 w-3/4" />
          <div className="h-4 bg-muted rounded w-1/2" />
        </div>
      ))}
    </div>
  );
};
