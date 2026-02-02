interface EmptyStateProps {
  title?: string;
  message?: string;
}

export const EmptyState = ({ 
  title = 'No products found', 
  message = 'Check back later for new products.' 
}: EmptyStateProps) => {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-16 text-center">
      <svg
        className="w-16 h-16 mx-auto mb-4 opacity-50 text-muted-foreground"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
        />
      </svg>
      <p className="text-lg font-medium text-foreground mb-2">{title}</p>
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
};
