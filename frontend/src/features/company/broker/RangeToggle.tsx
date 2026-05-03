import type { ChartRange } from "../../../shared/api/quotes";

const RANGES: ChartRange[] = ["1D", "1W", "1M", "6M", "1Y", "5Y", "MAX"];

interface RangeToggleProps {
  value: ChartRange;
  onChange: (next: ChartRange) => void;
}

export function RangeToggle({ value, onChange }: RangeToggleProps) {
  return (
    <div className="range-toggle" role="tablist" aria-label="Chart range">
      {RANGES.map((r) => (
        <button
          key={r}
          type="button"
          role="tab"
          aria-selected={r === value}
          className={`range-toggle__pill${r === value ? " is-active" : ""}`}
          onClick={() => onChange(r)}
        >
          {r}
        </button>
      ))}
    </div>
  );
}
