interface AreaChartProps {
  series: number[];
  stroke: string;
  gradientId: string;
  fillTop: string;
  fillBottom: string;
}

const VIEW_WIDTH = 680;
const VIEW_HEIGHT = 280;
const PADDING_TOP = 14;
const PADDING_BOTTOM = 10;

/** SVG area chart with gradient fill, ported from the design mockup's `areaSvg`. */
export function AreaChart({ series, stroke, gradientId, fillTop, fillBottom }: AreaChartProps) {
  const count = series.length;
  const min = Math.min(...series);
  const max = Math.max(...series);
  const plotHeight = VIEW_HEIGHT - PADDING_TOP - PADDING_BOTTOM;
  const scaleX = (index: number) => (index / (count - 1)) * VIEW_WIDTH;
  const scaleY = (value: number) => PADDING_TOP + ((max - value) / (max - min || 1)) * plotHeight;

  let linePath = `M${scaleX(0).toFixed(1)} ${scaleY(series[0]).toFixed(1)}`;
  for (let index = 1; index < count; index++) {
    linePath += ` L${scaleX(index).toFixed(1)} ${scaleY(series[index]).toFixed(1)}`;
  }
  const areaPath = `${linePath} L${VIEW_WIDTH} ${VIEW_HEIGHT} L0 ${VIEW_HEIGHT} Z`;

  const gridLines = [];
  for (let gridIndex = 0; gridIndex <= 3; gridIndex++) {
    const gridY = PADDING_TOP + (plotHeight * gridIndex) / 3;
    gridLines.push(
      <line
        key={`grid-${gridIndex}`}
        x1={0}
        x2={VIEW_WIDTH}
        y1={gridY}
        y2={gridY}
        stroke="var(--grid)"
        strokeWidth={1}
      />,
    );
  }

  return (
    <svg viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`} width="100%" style={{ display: "block", height: "auto" }}>
      <defs>
        <linearGradient id={gradientId} x1={0} y1={0} x2={0} y2={1}>
          <stop offset="0%" stopColor={fillTop} />
          <stop offset="100%" stopColor={fillBottom} />
        </linearGradient>
      </defs>
      {gridLines}
      <path d={areaPath} fill={`url(#${gradientId})`} />
      <path
        d={linePath}
        fill="none"
        stroke={stroke}
        strokeWidth={2.4}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={scaleX(count - 1)} cy={scaleY(series[count - 1])} r={5} fill={stroke} />
    </svg>
  );
}
