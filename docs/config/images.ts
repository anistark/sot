/**
 * Icons and the social preview image, drawn from sot's mark (images/sot.png,
 * traced in brand.ts): favicon.svg, favicon.ico, apple-touch-icon.png and the
 * Tokyo Night og.png.
 *
 * Text is set in Roboto Mono by turning glyphs into SVG paths (fontkit), so
 * the image looks the same on every machine, with no system fonts involved.
 */
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import * as fontkit from "fontkit";
import sharp from "sharp";
import { MARK, markShapes, markSvg, markWaves } from "./brand.ts";
import { DOCS_ROOT, sotData } from "./data.ts";

// Tokyo Night.
const C = {
  bgDark: "#16161e",
  bg: "#1a1b26",
  line: "#292e42",
  fg: "#c0caf5",
  fgDark: "#a9b1d6",
  comment: "#565f89",
  dark5: "#737aa2",
  blue: "#7aa2f7",
  cyan: "#7dcfff",
  magenta: "#bb9af7",
  green: "#9ece6a",
  yellow: "#e0af68",
  red: "#f7768e",
};

const FONT_DIR = path.join(DOCS_ROOT, "node_modules/@fontsource/roboto-mono/files");
type Font = ReturnType<typeof fontkit.openSync>;
const fonts = new Map<number, Font>();
function font(weight: 400 | 700): Font {
  if (!fonts.has(weight)) fonts.set(weight, fontkit.openSync(path.join(FONT_DIR, `roboto-mono-latin-${weight}-normal.woff2`)) as Font);
  return fonts.get(weight)!;
}

interface Run {
  svg: string;
  width: number;
}

/** A line of text as SVG paths, with its baseline at y. */
function text(str: string, x: number, y: number, size: number, fill: string, weight: 400 | 700 = 400): Run {
  const f = font(weight) as unknown as {
    unitsPerEm: number;
    layout(s: string): { glyphs: { path: { toSVG(): string } }[]; positions: { xAdvance: number }[]; advanceWidth: number };
  };
  const run = f.layout(str);
  const k = size / f.unitsPerEm;
  let advance = 0;
  const glyphs = run.glyphs.map((glyph, i) => {
    const d = glyph.path.toSVG();
    const out = d ? `<path transform="translate(${advance} 0)" d="${d}"/>` : "";
    advance += run.positions[i].xAdvance;
    return out;
  });
  return {
    svg: `<g fill="${fill}" transform="translate(${x} ${y}) scale(${k} ${-k})">${glyphs.join("")}</g>`,
    width: run.advanceWidth * k,
  };
}

/** The prompt arrow, drawn because Roboto Mono has no ❯. */
function chevron(x: number, y: number, size: number, stroke: string): string {
  const h = size * 0.34;
  return `<path d="M${x} ${y - h * 2}l${h} ${h}l${-h} ${h}" fill="none" stroke="${stroke}" stroke-width="${size * 0.1}" stroke-linecap="round" stroke-linejoin="round"/>`;
}

/** The mark at `size` pixels, its top-left corner at (x, y), inside a larger SVG. */
function placeMark(id: string, x: number, y: number, size: number, fill: string): string {
  const { square } = MARK;
  const k = size / square.size;
  const { defs, body } = markShapes(id, { fill });
  return `<defs>${defs}</defs><g transform="translate(${x - square.x * k} ${y - square.y * k}) scale(${k})">${body}</g>`;
}

/** iOS rounds the corners and wants no transparency: a full-bleed square with opaque waves. */
function touchIconSvg(size: number): string {
  const { square: s } = MARK;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${s.x} ${s.y} ${s.size} ${s.size}" width="${size}" height="${size}"><rect x="${s.x}" y="${s.y}" width="${s.size}" height="${s.size}" fill="#000"/>${markWaves("#fff")}</svg>`;
}

/** 1200×630 social preview: a terminal window running `sot --version`. */
function ogSvg(version: string): string {
  const W = 1200;
  const H = 630;
  const win = { x: 56, y: 56, w: W - 112, h: H - 112 };
  const parts: string[] = [];

  parts.push(
    `<defs>`,
    `<radialGradient id="glowA" cx="0.12" cy="0.05" r="0.6"><stop offset="0" stop-color="${C.blue}" stop-opacity="0.22"/><stop offset="1" stop-color="${C.blue}" stop-opacity="0"/></radialGradient>`,
    `<radialGradient id="glowB" cx="0.95" cy="1" r="0.6"><stop offset="0" stop-color="${C.magenta}" stop-opacity="0.2"/><stop offset="1" stop-color="${C.magenta}" stop-opacity="0"/></radialGradient>`,
    `<clipPath id="win"><rect x="${win.x}" y="${win.y}" width="${win.w}" height="${win.h}" rx="18"/></clipPath>`,
    `</defs>`,
    `<rect width="${W}" height="${H}" fill="${C.bgDark}"/>`,
    `<rect width="${W}" height="${H}" fill="url(#glowA)"/>`,
    `<rect width="${W}" height="${H}" fill="url(#glowB)"/>`,
    `<rect x="${win.x}" y="${win.y}" width="${win.w}" height="${win.h}" rx="18" fill="${C.bg}" stroke="${C.line}" stroke-width="2"/>`,
  );

  // Title bar.
  [C.red, C.yellow, C.green].forEach((fill, i) => parts.push(`<circle cx="${win.x + 34 + i * 26}" cy="${win.y + 32}" r="8" fill="${fill}"/>`));
  const title = text("~/sot/docs — zsh", 0, 0, 20, C.dark5);
  parts.push(text("~/sot/docs — zsh", W / 2 - title.width / 2, win.y + 39, 20, C.dark5).svg);
  parts.push(`<path d="M${win.x} ${win.y + 64}h${win.w}" stroke="${C.line}" stroke-width="2"/>`);

  // ~/sot ❯ sot --version
  const px = win.x + 64;
  const promptLine = (y: number, command: string) => {
    const cwd = text("~/sot", px, y, 26, C.cyan, 700);
    parts.push(cwd.svg, chevron(px + cwd.width + 18, y - 2, 26, C.blue));
    const cmd = text(command, px + cwd.width + 46, y, 26, C.fg, 700);
    parts.push(cmd.svg);
    return px + cwd.width + 46 + cmd.width;
  };
  promptLine(win.y + 128, "sot --version");

  // The mark, then what sot is.
  const markY = win.y + 162;
  const markSize = 150;
  parts.push(placeMark("mark", px, markY, markSize, C.fg));
  const tx = px + markSize + 56;
  parts.push(text("sot", tx, markY + 56, 60, C.fg, 700).svg);
  parts.push(text("System Observation Tool", tx, markY + 100, 28, C.blue, 700).svg);
  parts.push(text("A system monitor for the terminal,", tx, markY + 140, 24, C.fgDark).svg);
  parts.push(text("in the spirit of top.", tx, markY + 172, 24, C.fgDark).svg);

  // ~/sot ❯ uv tool install sot █
  const end = promptLine(win.y + 408, "uv tool install sot");
  parts.push(`<rect x="${end + 10}" y="${win.y + 386}" width="15" height="28" fill="${C.blue}"/>`);

  // tmux status bar.
  const sy = win.y + win.h - 44;
  parts.push(`<g clip-path="url(#win)"><rect x="${win.x}" y="${sy}" width="${win.w}" height="44" fill="${C.bgDark}"/>`);
  parts.push(`<rect x="${win.x}" y="${sy}" width="88" height="44" fill="${C.blue}"/>`);
  parts.push(text("[sot]", win.x + 14, sy + 29, 20, C.bg, 700).svg);
  let wx = win.x + 108;
  for (const [i, name] of ["readme", "install", "usage", "commands", "config"].entries()) {
    const label = `${i + 1}:${name}${i === 0 ? "*" : ""}`;
    const run = text(label, wx, sy + 29, 20, i === 0 ? C.blue : C.comment, i === 0 ? 700 : 400);
    parts.push(run.svg);
    wx += run.width + 24;
  }
  const ver = text(`v${version}`, 0, 0, 20, C.fg);
  parts.push(text(`v${version}`, win.x + win.w - ver.width - 24, sy + 29, 20, C.fg).svg, `</g>`);
  parts.push(`<rect x="${win.x}" y="${win.y}" width="${win.w}" height="${win.h}" rx="18" fill="none" stroke="${C.line}" stroke-width="2"/>`);

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${parts.join("")}</svg>`;
}

/** Wrap PNGs into one .ico (PNG-compressed entries, supported everywhere that matters). */
function ico(images: { size: number; png: Buffer }[]): Buffer {
  const header = Buffer.alloc(6 + images.length * 16);
  header.writeUInt16LE(0, 0);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(images.length, 4);
  let offset = header.length;
  images.forEach(({ size, png }, i) => {
    const entry = 6 + i * 16;
    header.writeUInt8(size >= 256 ? 0 : size, entry);
    header.writeUInt8(size >= 256 ? 0 : size, entry + 1);
    header.writeUInt16LE(1, entry + 4);
    header.writeUInt16LE(32, entry + 6);
    header.writeUInt32LE(png.length, entry + 8);
    header.writeUInt32LE(offset, entry + 12);
    offset += png.length;
  });
  return Buffer.concat([header, ...images.map((i) => i.png)]);
}

const png = (svg: string, size?: number) => {
  const image = sharp(Buffer.from(svg), { density: 300 });
  return (size ? image.resize(size, size) : image).png({ compressionLevel: 9 }).toBuffer();
};

let lastKey = "";

export async function buildImages(outputDir: string): Promise<void> {
  const version = sotData()?.version ?? "dev";
  if (version === lastKey) return;

  // Black like images/sot.png, white on a dark browser theme.
  const favicon = markSvg({
    id: "m",
    squareClass: "sq",
    head: "<style>.sq{fill:#000}@media (prefers-color-scheme:dark){.sq{fill:#fff}}</style>",
  });
  const icoMark = (size: number) => markSvg({ id: "m", fill: "#000", size });
  const [ico16, ico32, ico48, touchPng, og] = await Promise.all([
    png(icoMark(16), 16),
    png(icoMark(32), 32),
    png(icoMark(48), 48),
    png(touchIconSvg(180), 180),
    sharp(Buffer.from(ogSvg(version))).png({ compressionLevel: 9 }).toBuffer(),
  ]);

  await mkdir(outputDir, { recursive: true });
  await Promise.all([
    writeFile(path.join(outputDir, "favicon.svg"), favicon),
    writeFile(
      path.join(outputDir, "favicon.ico"),
      ico([
        { size: 16, png: ico16 },
        { size: 32, png: ico32 },
        { size: 48, png: ico48 },
      ]),
    ),
    writeFile(path.join(outputDir, "apple-touch-icon.png"), touchPng),
    writeFile(path.join(outputDir, "og.png"), og),
  ]);
  lastKey = version;
}
