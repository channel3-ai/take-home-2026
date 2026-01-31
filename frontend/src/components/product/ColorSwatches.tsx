import { getColorValue } from '../../utils/colors';

interface ColorSwatchesProps {
  colors: string[];
  maxVisible?: number;
}

export const ColorSwatches = ({ colors, maxVisible = 3 }: ColorSwatchesProps) => {
  if (!colors || colors.length === 0) return null;

  const visibleColors = colors.slice(0, maxVisible);
  const remainingCount = colors.length - maxVisible;

  return (
    <div className="flex gap-1.5 justify-center items-center">
      {visibleColors.map((color, colorIndex) => (
        <div
          key={colorIndex}
          className="w-4 h-4 rounded border border-border/20"
          style={{ backgroundColor: getColorValue(color) }}
          title={color}
        />
      ))}
      {remainingCount > 0 && (
        <span className="text-s text-muted-foreground font-medium ml-1">
          +{remainingCount} More
        </span>
      )}
    </div>
  );
};
