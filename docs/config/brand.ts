/**
 * sot's mark: a rounded square with ≈ cut out of it, as in images/sot.png.
 *
 * Traced from that 512×512 PNG, which it matches to within 0.1% of pixels.
 * Each wave is a stroke of straight 3:4 diagonals joined by round arcs, and
 * the waves are cut out (masked), so whatever is behind the mark shows through
 * them, as in the PNG.
 */

export const MARK = {
  /** The PNG's canvas. */
  canvas: 512,
  square: { x: 53, y: 53, size: 406, radius: 55 },
  stroke: 21.25,
  waves: [
    "M161.6,240.65L190.4,219.05A49 49 0 0 1 249.2,219.05L262.4,228.95A49 49 0 0 0 321.2,228.95L350,207.35",
    "M161.6,304.65L190.4,283.05A49 49 0 0 1 249.2,283.05L262.4,292.95A49 49 0 0 0 321.2,292.95L350,271.35",
  ],
} as const;

/** Margin kept around the square when the PNG's transparent border is cropped off. */
const CROP_MARGIN = 8;

interface Paint {
  /** Square colour; ignored when `squareClass` is set. */
  fill?: string;
  /** A class for the square instead of a fill, for SVGs that colour it with CSS. */
  squareClass?: string;
}

/** The mask and the square, in the PNG's 512-unit coordinates, to place inside any SVG. */
export function markShapes(id: string, { fill = "currentColor", squareClass }: Paint = {}): { defs: string; body: string } {
  const { square: s, stroke, waves } = MARK;
  const rect = `x="${s.x}" y="${s.y}" width="${s.size}" height="${s.size}" rx="${s.radius}"`;
  const cut = waves.map((d) => `<path d="${d}" fill="none" stroke="#000" stroke-width="${stroke}"/>`).join("");
  const paint = squareClass ? `class="${squareClass}"` : `fill="${fill}"`;
  return {
    defs: `<mask id="${id}"><rect ${rect} fill="#fff"/>${cut}</mask>`,
    body: `<rect ${rect} ${paint} mask="url(#${id})"/>`,
  };
}

/** The two waves on their own, as strokes, for icons that need them opaque. */
export function markWaves(stroke: string): string {
  return MARK.waves.map((d) => `<path d="${d}" fill="none" stroke="${stroke}" stroke-width="${MARK.stroke}"/>`).join("");
}

export interface MarkOptions extends Paint {
  /** Unique on the page: the mask is looked up by id. */
  id: string;
  className?: string;
  /** Read out by screen readers; without one the mark is decorative. */
  label?: string;
  /** Pixel size for the width and height attributes. */
  size?: number;
  /** Keep the PNG's transparent border instead of cropping close to the square. */
  padded?: boolean;
  /** Extra markup for the top of the SVG, such as a <style> block. */
  head?: string;
}

/** The mark as a standalone SVG. */
export function markSvg({ id, className, label, size, padded = false, head = "", ...paint }: MarkOptions): string {
  const { square: s } = MARK;
  const viewBox = padded
    ? `0 0 ${MARK.canvas} ${MARK.canvas}`
    : `${s.x - CROP_MARGIN} ${s.y - CROP_MARGIN} ${s.size + 2 * CROP_MARGIN} ${s.size + 2 * CROP_MARGIN}`;
  const { defs, body } = markShapes(id, paint);
  const attrs = [
    `xmlns="http://www.w3.org/2000/svg"`,
    `viewBox="${viewBox}"`,
    size ? `width="${size}" height="${size}"` : "",
    className ? `class="${className}"` : "",
    label ? `role="img" aria-label="${label}"` : `aria-hidden="true"`,
  ].filter(Boolean);
  return `<svg ${attrs.join(" ")}>${head}<defs>${defs}</defs>${body}</svg>`;
}
