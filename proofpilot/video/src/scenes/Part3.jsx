import React from 'react';
import { useCurrentFrame, staticFile, Audio } from 'remotion';
import { Backdrop, Grid, Kicker, Headline, Sub, Panel, Chip, Caption, Check } from '../components/Ui';
import { C, fade, rise, clamp01 } from '../theme';

const Verse = ({ frame, dur, audio, children }) => (
  <>
    <Audio src={staticFile(audio)} />
    <div style={{ flex: 1, opacity: fade(frame, dur), position: 'relative' }}>{children}</div>
  </>
);

export const S08_ServerWrite = ({ dur, audio }) => {
  const f = useCurrentFrame();
  const items = [
    { l: 'Target supplier', at: 60 },
    { l: 'Allowed field', at: 100 },
    { l: 'Approved value', at: 140 },
    { l: 'Record version', at: 180 },
    { l: 'Approval re-checked at commit', at: 220 },
  ];
  const branches = clamp01((f - 300) / 20);
  return (
    <Backdrop>
      <Grid />
      <Verse frame={f} dur={dur} audio={audio}>
        <Kicker>Step four · the commit</Kicker>
        <Headline size={58} width={1200}>
          The browser never writes. <span style={{ color: C.brand2 }}>The server does.</span>
        </Headline>
        <div style={{ display: 'flex', gap: 44, marginTop: 46 }}>
          <Panel style={{ flex: 1, padding: 30 }}>
            <div style={{ fontSize: 20, color: C.brand2, marginBottom: 22, fontFamily: C.mono }}>server-side capability</div>
            {items.map((it) => (
              <Check key={it.l} frame={f} delay={it.at} done={f > it.at + 8} label={it.l} />
            ))}
            <div style={{ marginTop: 22, fontFamily: C.mono, fontSize: 17, color: C.dimmer }}>
              PATCH /suppliers/SUP-1001 · idem key run:row:v1
            </div>
          </Panel>
          <div style={{ width: 620 }}>
            <div style={{ ...rise(f, 300) }}>
              <Panel pad={26} style={{ marginBottom: 18 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <span style={{ fontFamily: C.mono, fontSize: 14, padding: '5px 10px', borderRadius: 7, background: '#2A2110', color: C.warn, border: `1px solid ${C.warn}55` }}>
                    CANCEL
                  </span>
                  <span style={{ fontSize: 24, fontWeight: 600 }}>Cancelled before commit</span>
                </div>
                <div style={{ fontSize: 19, color: C.dim, marginTop: 10 }}>Write never happens. Record unchanged.</div>
              </Panel>
            </div>
            <div style={{ ...rise(f, 330) }}>
              <Panel pad={26}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <span style={{ fontFamily: C.mono, fontSize: 14, padding: '5px 10px', borderRadius: 7, background: '#12281f', color: C.ok, border: `1px solid ${C.ok}55` }}>
                    RECONCILE
                  </span>
                  <span style={{ fontSize: 24, fontWeight: 600 }}>Lost acknowledgement</span>
                </div>
                <div style={{ fontSize: 19, color: C.dim, marginTop: 10 }}>
                  State reconciled from the durable record — never a blind retry, never a second write.
                </div>
              </Panel>
            </div>
            <div style={{ marginTop: 20, opacity: branches, fontSize: 19, color: C.dimmer, lineHeight: 1.6 }}>
              Ambiguous outcomes stay unresolved and block further attempts until a human reconciles them.
            </div>
          </div>
        </div>
        <Caption>Authority lives on the server, not in the model's transcript.</Caption>
      </Verse>
    </Backdrop>
  );
};

export const S09_Readback = ({ dur, audio }) => {
  const f = useCurrentFrame();
  const rows = [
    { l: 'Observed value', e: '12 Canal Road, Amsterdam', o: '12 Canal Road, Amsterdam', ok: true, at: 110 },
    { l: 'Record version', e: 'v1 → v2', o: 'v1 → v2', ok: true, at: 150 },
    { l: 'Bank account hash', e: 'unchanged', o: 'unchanged', ok: true, at: 190 },
    { l: 'Tax identifier hash', e: 'unchanged', o: 'unchanged', ok: true, at: 230 },
  ];
  const verified = clamp01((f - 280) / 22);
  const exp = clamp01((f - 340) / 20);
  return (
    <Backdrop tint="#2ED3A7">
      <Grid />
      <Verse frame={f} dur={dur} audio={audio}>
        <Kicker>Step five · read-back</Kicker>
        <Headline size={58} width={1240}>
          Don't take the agent's word for it. <span style={{ color: C.ok }}>Read it back.</span>
        </Headline>
        <div style={{ display: 'flex', gap: 44, marginTop: 44 }}>
          <Panel style={{ flex: 1, padding: 30 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 22 }}>
              <div>
                <div style={{ fontSize: 22, fontWeight: 650 }}>Writer</div>
                <div style={{ fontSize: 18, color: C.dimmer }}>scoped capability</div>
              </div>
              <div style={{ color: C.dimmer, fontSize: 34 }}>→</div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 22, fontWeight: 650, color: C.ok }}>Verifier</div>
                <div style={{ fontSize: 18, color: C.dimmer }}>separate read-only identity</div>
              </div>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 21 }}>
              <thead>
                <tr style={{ color: C.dimmer, fontSize: 14, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  <th style={{ textAlign: 'left', paddingBottom: 10 }}>Check</th>
                  <th style={{ textAlign: 'left' }}>Expected</th>
                  <th style={{ textAlign: 'left' }}>Observed</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const on = clamp01((f - r.at) / 14);
                  if (!on) return null;
                  return (
                    <tr key={r.l} style={{ opacity: on }}>
                      <td style={{ padding: '12px 0', borderTop: `1px solid ${C.line}66`, color: C.dim }}>{r.l}</td>
                      <td style={{ padding: '12px 10px', borderTop: `1px solid ${C.line}66`, color: C.ink }}>{r.e}</td>
                      <td style={{ padding: '12px 0', borderTop: `1px solid ${C.line}66`, color: r.ok ? C.ok : C.bad }}>{r.o}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div
              style={{
                marginTop: 24,
                padding: '14px 20px',
                borderRadius: 12,
                display: 'inline-block',
                background: verified ? '#0E2A21' : '#10162a',
                border: `1px solid ${verified ? C.ok : C.line}`,
                color: verified ? C.ok : C.dimmer,
                fontSize: 25,
                fontWeight: 650,
                fontFamily: C.mono,
                opacity: Math.max(verified, 0.35),
              }}
            >
              {verified ? 'VERIFIED' : 'comparing…'}
            </div>
          </Panel>
          <Panel style={{ width: 520, padding: 30 }}>
            <div style={{ fontSize: 22, fontWeight: 650, marginBottom: 18 }}>Evidence, one file</div>
            <div style={{ fontSize: 19, color: C.dim, lineHeight: 1.7, marginBottom: 22 }}>
              Source contract, selected target, model provenance, action timeline, read-back result — exportable as report, JSON or ZIP.
            </div>
            <div style={{ opacity: exp }}>
              {['chain', 'timeline', 'provenance', 'export.zip'].map((c) => (
                <Chip key={c} tone={C.ok} bg="#0E2A21">
                  {c}
                </Chip>
              ))}
            </div>
            <div style={{ marginTop: 26, fontSize: 18, color: C.dimmer, lineHeight: 1.6 }}>
              Verification is point-in-time and attests to what the record said at that moment.
            </div>
          </Panel>
        </div>
        <Caption>Only a successful read-back earns the word verified.</Caption>
      </Verse>
    </Backdrop>
  );
};

export const S10_Results = ({ dur, audio }) => {
  const f = useCurrentFrame();
  // Each metric lands as the narration says it: 7/7 ~1s, 0/18 ~7s, 11/11 ~11s, 9/9 ~17s.
  const metrics = [
    { n: 7, d: 7, l: 'authorised changes completed and verified', s: '/', at: 40 },
    { n: 0, d: 18, l: 'unauthorised mutations', s: '/', at: 200 },
    { n: 11, d: 11, l: 'failures surfaced, none silently retried', s: '/', at: 330 },
    { n: 9, d: 9, l: 'model runs completed where completion was possible', s: '/', at: 520 },
  ];
  const outroAt = Math.max(700, dur - 210);
  const outro = clamp01((f - outroAt) / 26);
  return (
    <Backdrop tint="#6C5CE7">
      <Grid />
      <Verse frame={f} dur={dur} audio={audio}>
        <Kicker>Measured</Kicker>
        <Headline size={56} width={1180}>
          Every run measured. <span style={{ color: C.brand2 }}>Nothing assumed.</span>
        </Headline>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 26, marginTop: 42 }}>
          {metrics.map((m) => {
            const t = clamp01((f - m.at) / 30);
            const val = Math.round(m.n * t);
            return (
              <Panel key={m.l} style={{ padding: 28, opacity: Math.max(t, 0.25) }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
                  <span style={{ fontSize: 66, fontWeight: 700, letterSpacing: '-0.03em', color: m.n === 0 ? C.ok : C.ink }}>{val}</span>
                  <span style={{ fontSize: 30, color: C.dimmer, fontFamily: C.mono }}>{m.s} {m.d}</span>
                </div>
                <div style={{ fontSize: 21, color: C.dim, marginTop: 10 }}>{m.l}</div>
              </Panel>
            );
          })}
        </div>
        <div
          style={{
            marginTop: 20,
            opacity: clamp01((f - 575) / 26),
            fontSize: 18,
            color: C.dimmer,
            fontFamily: C.mono,
            letterSpacing: '0.01em',
          }}
        >
          live-model completion across four identical suites: 9 · 6 · 8 · 9 of 12 — figures above are the final run
        </div>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: `radial-gradient(900px 600px at 50% 50%, #0A0D18 0%, #080B14 70%)`,
            opacity: outro,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 18,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <div style={{ width: 62, height: 62, borderRadius: 17, background: `linear-gradient(140deg, ${C.brand}, ${C.brand2})`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 30, fontWeight: 700 }}>✳</div>
            <div style={{ fontSize: 54, fontWeight: 700, letterSpacing: '-0.03em' }}>ProofPilot</div>
          </div>
          <div style={{ fontSize: 27, color: C.dim }}>Contract · Bounded action · Independent read-back</div>
          <div style={{ fontSize: 22, color: C.dimmer, fontFamily: C.mono, marginTop: 10 }}>
            agents that act — and systems you can check
          </div>
        </div>
      </Verse>
    </Backdrop>
  );
};
