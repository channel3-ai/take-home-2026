import { useNavigate } from 'react-router-dom';

interface BackButtonProps {
  to?: string;
  label?: string;
  className?: string;
}

export const BackButton = ({ 
  to = '/', 
  label = 'Back to Catalog',
  className = 'flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-4'
}: BackButtonProps) => {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate(to)}
      className={className}
    >
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 19l-7-7 7-7"
        />
      </svg>
      {label}
    </button>
  );
};
