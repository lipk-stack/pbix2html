export function formatNumber(value: number | null, formatString?: string): string {
  if (value === null) return "-";

  const isCurrency = formatString?.includes("$") ?? false;
  const isPercent = formatString?.includes("%") ?? false;

  if (isPercent) return `${(value * 100).toFixed(1)}%`;

  const rounded = Math.round(value * 100) / 100;
  const grouped = rounded.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return isCurrency ? `$${grouped}` : grouped;
}
