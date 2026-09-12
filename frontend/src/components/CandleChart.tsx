import type { Candle } from "../types";

interface CandleChartProps {
  data: Candle[];
}

const VIEW_WIDTH = 680;
const VIEW_HEIGHT = 280;
const PADDING_X = 10;
const PADDING_TOP = 12;
const PADDING_BOTTOM = 14;

/** SVG candlestick chart, ported from the design mockup's `candleSvg`. */
export function CandleChart({ data }: CandleChartProps) {
  const count = data.length;
  const slotWidth = (VIEW_WIDTH - PADDING_X * 2) / count;
  const bodyWidth = Math.min(15, slotWidth * 0.6);
  const extremes = data.flatMap((candle) => [candle.high, candle.low]);
  const max = Math.max(...extremes);
  const min = Math.min(...extremes);
  const plotHeight = VIEW_HEIGHT - PADDING_TOP - PADDING_BOTTOM;
  const scaleY = (value: number) => PADDING_TOP + ((max - value) / (max - min || 1)) * plotHeight;

  const gridLines = [];
  for (let gridIndex = 0; gridIndex <= 3; gridIndex++) {
    const gridY = PADDING_TOP + (plotHeight * gridIndex) / 3;
    gridLines.push(
      <line
        key={`grid-${gridIndex}`}
        x1={PADDING_X}
        x2={VIEW_WIDTH - PADDING_X}
        y1={gridY}
        y2={gridY}
        stroke="var(--grid)"
        strokeWidth={1}
      />,
    );
  }

  const candles = data.map((candle, index) => {
    const centerX = PADDING_X + slotWidth * index + slotWidth / 2;
    const isUp = candle.close >= candle.open;
    const color = isUp ? "var(--up)" : "var(--down)";
    const openY = scaleY(candle.open);
    const closeY = scaleY(candle.close);
    const bodyTop = Math.min(openY, closeY);
    const bodyHeight = Math.max(2, Math.abs(closeY - openY));
    return (
      <g key={index}>
        <line
          x1={centerX}
          x2={centerX}
          y1={scaleY(candle.high)}
          y2={scaleY(candle.low)}
          stroke={color}
          strokeWidth={1.5}
        />
        <rect x={centerX - bodyWidth / 2} y={bodyTop} width={bodyWidth} height={bodyHeight} fill={color} rx={1.5} />
      </g>
    );
  });

  return (
    <svg viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`} width="100%" style={{ display: "block", height: "auto" }}>
      {gridLines}
      {candles}
    </svg>
  );
}
