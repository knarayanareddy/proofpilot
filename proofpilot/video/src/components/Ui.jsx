import React from 'react';
import { C, clamp01 } from '../theme';

export const Backdrop = ({ children, tint = C.brand }) => (
  <div
    style={{
      flex: 1,
      background: `radial-gradient(1200px 800px at 78% 12%, ${tint}22 0%, transparent 60%), radial-gradient(900px 700px at 8% 92%, #12d3a715 0%, transparent 55%), linear-gradient(180deg, ${C.bg} 0%, ${C.bg2} 100%)`,
      display: 'flex',
      flexDirection: 'column',
      padding: '86px 110px 118px',
      fontFamily: C.sans,
      color: C.ink,
      position: 'relative',
    }}
  >
    {children}
  </div>
);

export const Grid = () => (
  <div
    style={{
      position: 'absolute',
      inset: 0,
      opacity: 0.16,
      backgroundImage: `linear-gradient(${C.line}55 1px, transparent 1px), linear-gradient(90deg, ${C.line}55 1px, transparent 1px)`,
      backgroundSize: '60px 60px',
      maskImage: 'radial-gradient(circle at 50% 40%, black 0%, transparent 78%)',
      WebkitMaskImage: 'radial-gradient(circle at 50% 40%, black 0%, transparent 78%)',
    }}
  />
);

export const Kicker = ({ children, color = C.brand2 }) => (
  <div style={{ fontSize: 20, letterSpacing: '0.22em', textTransform: 'uppercase', color, fontWeight: 600, marginBottom: 18 }}>
    {children}
  </div>
);

export const Headline = ({ children, size = 72, width = 1180 }) => (
  <div style={{ fontSize: size, lineHeight: 1.06, fontWeight: 700, letterSpacing: '-0.03em', maxWidth: width }}>{children}</div>
);

export const Sub = ({ children, size = 30, width = 1080 }) => (
  <div style={{ fontSize: size, lineHeight: 1.45, color: C.dim, maxWidth: width, marginTop: 22, fontWeight: 400 }}>{children}</div>
);

export const Panel = ({ children, style = {}, pad = 30, radius = 18, tone = C.panel }) => (
  <div
    style={{
      background: tone,
      border: `1px solid ${C.line}`,
      borderRadius: radius,
      padding: pad,
      boxShadow: '0 30px 70px rgba(0,0,0,0.45)',
      ...style,
    }}
  >
    {children}
  </div>
);

export const BrowserFrame = ({ children, label = 'supplier record', width = 720 }) => (
  <div style={{ width, background: C.panel, border: `1px solid ${C.line}`, borderRadius: 16, overflow: 'hidden', boxShadow: '0 30px 60px rgba(0,0,0,0.5)' }}>
    <div style={{ height: 42, background: C.panel2, borderBottom: `1px solid ${C.line}`, display: 'flex', alignItems: 'center', padding: '0 16px', gap: 8 }}>
      {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => (
        <div key={c} style={{ width: 11, height: 11, borderRadius: 6, background: c }} />
      ))}
      <div style={{ marginLeft: 14, fontSize: 14, color: C.dimmer, fontFamily: C.mono }}>{label}</div>
    </div>
    <div style={{ padding: 28 }}>{children}</div>
  </div>
);

export const Field = ({ label, value, highlight = false, changed = false, width = '100%' }) => (
  <div style={{ marginBottom: 18 }}>
    <div style={{ fontSize: 13, letterSpacing: '0.08em', textTransform: 'uppercase', color: C.dimmer, marginBottom: 7 }}>{label}</div>
    <div
      style={{
        width,
        padding: '13px 15px',
        borderRadius: 10,
        background: changed ? '#12281f' : '#0B1020',
        border: `1px solid ${highlight ? C.brand2 : changed ? C.ok : C.line}`,
        color: highlight || changed ? C.ink : C.dim,
        fontFamily: C.mono,
        fontSize: 19,
        boxShadow: highlight ? `0 0 0 4px ${C.brand}33` : 'none',
      }}
    >
      {value}
    </div>
  </div>
);

export const Chip = ({ children, tone = C.brand2, bg = '#1A1738' }) => (
  <span
    style={{
      display: 'inline-block',
      padding: '6px 12px',
      borderRadius: 8,
      background: bg,
      color: tone,
      fontFamily: C.mono,
      fontSize: 15,
      border: `1px solid ${tone}44`,
      marginRight: 8,
    }}
  >
    {children}
  </span>
);

export const Check = ({ done, label, delay = 0, frame }) => {
  const t = clamp01((frame - delay) / 12);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16, opacity: t }}>
      <div
        style={{
          width: 30,
          height: 30,
          borderRadius: 9,
          border: `2px solid ${done ? C.ok : C.line}`,
          background: done ? '#0F2A22' : 'transparent',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: C.ok,
          fontSize: 18,
          fontWeight: 700,
          transform: `scale(${0.8 + 0.2 * t})`,
        }}
      >
        {done ? '✓' : ''}
      </div>
      <div style={{ fontSize: 24, color: done ? C.ink : C.dim }}>{label}</div>
    </div>
  );
};

export const Caption = ({ children }) => (
  <div
    style={{
      position: 'absolute',
      left: 110,
      right: 110,
      bottom: 54,
      display: 'flex',
      justifyContent: 'center',
    }}
  >
    <div
      style={{
        padding: '12px 26px',
        borderRadius: 999,
        background: 'rgba(9,12,22,0.72)',
        border: `1px solid ${C.line}`,
        color: C.dim,
        fontSize: 23,
        letterSpacing: '0.01em',
        backdropFilter: 'blur(6px)',
      }}
    >
      {children}
    </div>
  </div>
);
