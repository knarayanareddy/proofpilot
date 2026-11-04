import React from 'react';
import { useCurrentFrame, staticFile, Audio } from 'remotion';
import { Backdrop, Grid, Kicker, Headline, Sub, Panel, Chip, Caption, BrowserFrame, Field, Check } from '../components/Ui';
import { C, fade, rise, clamp01 } from '../theme';

const Verse = ({ frame, dur, audio, children }) => (
  <>
    <Audio src={staticFile(audio)} />
    <div style={{ flex: 1, opacity: fade(frame, dur), position: 'relative' }}>{children}</div>
  </>
);

export const S05_Ambiguity = ({ dur, audio }) => {
  const f = useCurrentFrame();
  const stop = clamp01((f - 90) / 18);
  const expire = clamp01((f - 210) / 20);
  const moved = clamp01((f - 300) / 18);
  const seconds = Math.max(0, 300 - Math.floor((f - 210) / 3));
  return (
    <Backdrop>
      <Grid />
      <Verse frame={f} dur={dur} audio={audio}>
        <Kicker>Step two · matching</Kicker>
        <Headline size={58} width={1240}>
          When two records look alike, <span style={{ color: C.warn }}>it stops</span>.
        </Headline>
        <div style={{ display: 'flex', gap: 40, marginTop: 48 }}>
          <div style={{ flex: 1 }}>
            {[
              { n: 'Northstar Supply BV', a: '10 North Road, Rotterdam', v: 1 },
              { n: 'Northstar Supply Europe', a: '22 Star Road, Rotterdam', v: 1 },
            ].map((c, i) => (
              <Panel key={c.n} style={{ padding: 24, marginBottom: 18, ...rise(f, 40 + i * 24) }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 27, fontWeight: 600 }}>{c.n}</div>
                    <div style={{ fontSize: 20, color: C.dim, marginTop: 6 }}>{c.a}</div>
                  </div>
                  <div style={{ fontFamily: C.mono, color: C.dimmer, fontSize: 17 }}>v{c.v}</div>
                </div>
              </Panel>
            ))}
            <div style={{ ...rise(f, 150), display: 'flex', gap: 12, marginTop: 8 }}>
              <button style={{ pointerEvents: 'none', background: C.panel2, border: `1px solid ${C.line}`, borderRadius: 10, padding: '12px 18px', color: C.ink, fontSize: 19 }}>
                Select candidate
              </button>
              <button style={{ pointerEvents: 'none', background: 'transparent', border: `1px solid ${C.bad}55`, borderRadius: 10, padding: '12px 18px', color: C.bad, fontSize: 19 }}>
                Reject all
              </button>
            </div>
          </div>
          <Panel style={{ width: 520, padding: 30 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, opacity: stop }}>
              <div style={{ width: 42, height: 42, borderRadius: 12, background: '#2A2110', border: `1px solid ${C.warn}66`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.warn, fontSize: 24 }}>
                ⏸
              </div>
              <div style={{ fontSize: 25, fontWeight: 600, color: C.warn }}>Paused for a human</div>
            </div>
            <div style={{ marginTop: 26, opacity: expire }}>
              <div style={{ fontSize: 19, color: C.dimmer, marginBottom: 8 }}>selection expires in</div>
              <div style={{ fontFamily: C.mono, fontSize: 42, color: C.ink }}>
                {String(Math.floor(seconds / 60))}:{String(seconds % 60).padStart(2, '0')}
              </div>
            </div>
            <div
              style={{
                marginTop: 26,
                padding: 18,
                borderRadius: 12,
                background: moved ? '#2A1218' : '#0E1424',
                border: `1px solid ${moved ? C.bad + '66' : C.line}`,
                opacity: moved ? 1 : 0.35,
              }}
            >
              <div style={{ fontSize: 22, color: moved ? C.bad : C.dim, fontWeight: 600 }}>Record version changed</div>
              <div style={{ fontSize: 19, color: C.dim, marginTop: 8 }}>
                Approval invalidated — nothing was written.
              </div>
            </div>
          </Panel>
        </div>
        <Caption>No silent pick. A guess that writes is worse than a pause.</Caption>
      </Verse>
    </Backdrop>
  );
};

export const S06_Model = ({ dur, audio }) => {
  const f = useCurrentFrame();
  const scan = ((f - 40) % 140) / 140;
  const steps = [
    { at: 60, t: 'click 412, 318', r: 'resolve → shipping field', ok: true },
    { at: 150, t: "type '12 Canal Road, Amsterdam'", r: 'value matches contract', ok: true },
    { at: 250, t: 'click 1031, 648', r: 'outside approved controls', ok: false },
    { at: 340, t: 'run stopped · 0 writes', r: 'nothing executed', ok: false },
  ];
  return (
    <Backdrop tint="#6C5CE7">
      <Grid />
      <Verse frame={f} dur={dur} audio={audio}>
        <Kicker>Step three · the model proposes</Kicker>
        <Headline size={56} width={1180}>
          A Meta model reads the screen. <span style={{ color: C.brand2 }}>The runtime decides.</span>
        </Headline>
        <div style={{ display: 'flex', gap: 40, marginTop: 42 }}>
          <div style={{ position: 'relative' }}>
            <BrowserFrame label="isolated browser · supplier record" width={660}>
              <div style={{ fontSize: 22, fontWeight: 600, marginBottom: 6 }}>Harbor Parts</div>
              <div style={{ fontSize: 18, color: C.dimmer, fontFamily: C.mono, marginBottom: 22 }}>SUP-1001</div>
              <Field label="Shipping address" value="1 Old Quay, Amsterdam" highlight={f > 60 && f < 250} changed={f >= 250} />
              <Field label="Bank account (out of scope)" value="████ ████ ████ 4417" />
              <div style={{ marginTop: 10, fontSize: 17, color: C.dimmer }}>
                {f > 150 ? 'Model entry: 12 Canal Road, Amsterdam' : 'Awaiting model action…'}
              </div>
            </BrowserFrame>
            <div
              style={{
                position: 'absolute',
                left: 0,
                right: 0,
                top: 42 + scan * 250,
                height: 3,
                background: `linear-gradient(90deg, transparent, ${C.brand2}, transparent)`,
                opacity: f > 40 && f < 380 ? 0.9 : 0,
              }}
            />
          </div>
          <Panel style={{ flex: 1, padding: 28 }}>
            <div style={{ fontSize: 20, color: C.brand2, marginBottom: 18, fontFamily: C.mono }}>policy gate</div>
            {steps.map((s, i) => {
              const on = clamp01((f - s.at) / 14);
              if (!on) return null;
              return (
                <div key={s.t} style={{ marginBottom: 18, opacity: on }}>
                  <div style={{ fontFamily: C.mono, fontSize: 19, color: C.ink }}>{s.t}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8 }}>
                    <span
                      style={{
                        fontFamily: C.mono,
                        fontSize: 15,
                        padding: '5px 11px',
                        borderRadius: 7,
                        background: s.ok ? '#0F2A22' : '#2A1218',
                        color: s.ok ? C.ok : C.bad,
                        border: `1px solid ${s.ok ? C.ok + '55' : C.bad + '55'}`,
                      }}
                    >
                      {s.ok ? 'ALLOW' : 'DENIED'}
                    </span>
                    <span style={{ fontSize: 19, color: C.dim }}>{s.r}</span>
                  </div>
                </div>
              );
            })}
            <div style={{ marginTop: 22, paddingTop: 18, borderTop: `1px solid ${C.line}`, fontSize: 18, color: C.dimmer, lineHeight: 1.6 }}>
              Unknown action types and unresolved clicks stop the run. Safety checks are never waved through.
            </div>
          </Panel>
        </div>
        <Caption>Every proposal is filtered before it is executed — including the one you wanted.</Caption>
      </Verse>
    </Backdrop>
  );
};

export const S07_Sandbox = ({ dur, audio }) => {
  const f = useCurrentFrame();
  const checks = [
    { l: 'Host port unreachable', at: 120 },
    { l: 'External network unreachable', at: 150 },
    { l: 'System paths read-only', at: 180 },
    { l: 'Workspace not mounted', at: 210 },
    { l: 'Model key absent from worker', at: 240 },
  ];
  const cage = clamp01((f - 50) / 22);
  return (
    <Backdrop>
      <Grid />
      <Verse frame={f} dur={dur} audio={audio}>
        <Kicker>Isolation</Kicker>
        <Headline size={58} width={1180}>
          The browser is a guest. <span style={{ color: C.ok }}>With nothing to reach.</span>
        </Headline>
        <div style={{ display: 'flex', gap: 46, marginTop: 50 }}>
          <div style={{ position: 'relative', width: 700 }}>
            <div
              style={{
                position: 'absolute',
                inset: -34,
                border: `2px dashed ${C.ok}88`,
                borderRadius: 26,
                opacity: cage,
                transform: `scale(${0.94 + cage * 0.06})`,
              }}
            />
            <div
              style={{
                position: 'absolute',
                top: -58,
                left: 0,
                fontFamily: C.mono,
                fontSize: 16,
                color: C.ok,
                opacity: cage,
                background: '#0C1F1A',
                padding: '6px 12px',
                borderRadius: 8,
                border: `1px solid ${C.ok}44`,
              }}
            >
              sandbox · namespaces: net / user / pid / ipc
            </div>
            <BrowserFrame label="browser process" width={700}>
              <div style={{ fontSize: 21, marginBottom: 18, color: C.dim }}>Rendered form, no extensions, no downloads.</div>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {['network', 'filesystem', 'credentials', 'model key'].map((x, i) => (
                  <div
                    key={x}
                    style={{
                      ...rise(f, 90 + i * 20),
                      padding: '10px 14px',
                      borderRadius: 9,
                      border: `1px solid ${C.bad}55`,
                      background: '#1C1116',
                      color: '#FF8A93',
                      fontFamily: C.mono,
                      fontSize: 16,
                      textDecoration: 'line-through',
                    }}
                  >
                    {x}
                  </div>
                ))}
              </div>
            </BrowserFrame>
          </div>
          <Panel style={{ flex: 1, padding: 30 }}>
            <div style={{ fontSize: 20, color: C.ok, marginBottom: 20, fontFamily: C.mono }}>probes before any action</div>
            {checks.map((c) => (
              <Check key={c.l} frame={f} delay={c.at} done={f > c.at + 8} label={c.l} />
            ))}
            <div style={{ marginTop: 18, fontSize: 19, color: C.dimmer, lineHeight: 1.6 }}>
              If a probe fails, execution stops. There is no unsandboxed fallback path.
            </div>
          </Panel>
        </div>
        <Caption>Isolation is measured, not asserted.</Caption>
      </Verse>
    </Backdrop>
  );
};
