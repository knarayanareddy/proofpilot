export const fps = 30;
export const width = 1920;
export const height = 1080;

export const C = {
  bg: '#080B14',
  bg2: '#0E1322',
  panel: '#141A2C',
  panel2: '#1B2338',
  line: '#27304A',
  ink: '#F4F7FF',
  dim: '#97A2C0',
  dimmer: '#5C688A',
  brand: '#6C5CE7',
  brand2: '#9B8CFF',
  ok: '#2ED3A7',
  warn: '#F5B544',
  bad: '#FF5C6C',
  mono: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
  sans: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
};

export const fade = (frame, duration, inFrames = 10, outFrames = 12) => {
  const inA = Math.min(1, frame / inFrames);
  const outA = Math.min(1, Math.max(0, (duration - frame) / outFrames));
  return Math.min(inA, outA);
};

export const rise = (frame, delay = 0, distance = 28) => {
  const t = Math.max(0, Math.min(1, (frame - delay) / 18));
  const eased = 1 - Math.pow(1 - t, 3);
  return { transform: `translateY(${(1 - eased) * distance}px)`, opacity: eased };
};

export const clamp01 = (v) => Math.max(0, Math.min(1, v));
export const lerp = (a, b, t) => a + (b - a) * clamp01(t);
