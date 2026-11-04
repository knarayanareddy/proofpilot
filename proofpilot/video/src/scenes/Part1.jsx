import React from 'react';
import { useCurrentFrame, staticFile, Audio } from 'remotion';
import { Backdrop, Grid, Kicker, Headline, Sub, Panel, Chip, Caption, Field } from '../components/Ui';
import { C, fade, rise, clamp01 } from '../theme';

const Verse = ({ frame, dur, audio, children }) => (
  <>
    <Audio src={staticFile(audio)} />
    <div style={{ flex: 1, opacity: fade(frame, dur), position: 'relative' }}>
      {children}
    </div>
  </>
);

export const S01_Hook = ({ dur, audio }) => {
  const f = useCurrentFrame();
  const bank = clamp01((f - 150) / 20);
  const gone = clamp01((f - 240) / 22);
  const title = clamp01((f - 330) / 24);
  return (
    <Backdrop tint="#FF5C6C">
      <Grid />
      <Verse frame={f} dur={dur} audio={audio}>
        <div style={{ display: 'flex', gap: 70 }}>
          <div style={{ flex: 1.15, paddingTop: 40 }}>
            <Kicker color="#FF8A93">Business email compromise</Kicker>
            <Headline size={66}>
              The supplier email
              <br />
              that becomes a
              <br />
              <span style={{ color: C.bad }}>payment fraud.</span>
            </Headline>
            <Sub size={27} width={720}>
              Same sender. Same tone. One small change to a record — and then the money moves.
            </Sub>
          </div>
          <div style={{ flex: 1, paddingTop: 26 }}>
            <Panel pad={0} style={{ overflow: 'hidden' }}>
              <div style={{ padding: '14px 22px', borderBottom: `1px solid ${C.line}`, display: 'flex', justifyContent: 'space-between', color: C.dimmer, fontSize: 15 }}>
                <span>accounts-payable@inbox</span>
                <span style={{ fontFamily: C.mono }}>09:41</span>
              </div>
              <div style={{ padding: 24, fontFamily: C.mono, fontSize: 19, lineHeight: 1.9, color: C.dim }}>
                <div style={rise(f, 20)}>From: north.supply@…</div>
                <div style={rise(f, 34)}>Subject: Updated shipping address</div>
                <div style={{ height: 1, background: C.line, margin: '16px 0' }} />
                <div style={rise(f, 52)}>Please ship to:</div>
                <div style={{ ...rise(f, 66), color: C.ink }}>12 Canal Road, Amsterdam</div>
                <div style={{ height: 1, background: C.line, margin: '16px 0' }} />
                <div style={{ ...rise(f, 110), color: bank ? C.bad : C.dim, opacity: Math.max(rise(f, 110).opacity, bank * 0.0) + bank * 0.0 }}>
                  Also update our bank details:
                </div>
                <div
                  style={{
                    color: bank ? C.bad : C.dimmer,
                    opacity: 0.35 + bank * 0.65,
                    textDecoration: gone ? 'line-through' : 'none',
                    filter: gone ? 'saturate(0.4)' : 'none',
                  }}
                >
                  IBAN ████████████
                </div>
                <div style={{ marginTop: 20, opacity: gone, color: C.bad, fontSize: 21, fontWeight: 600 }}>Payment redirected.</div>
              </div>
            </Panel>
          </div>
        </div>
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: 150,
            textAlign: 'center',
            opacity: title,
            transform: `translateY(${(1 - title) * 18}px)`,
          }}
        >
          <div style={{ fontSize: 58, fontWeight: 700, letterSpacing: '-0.03em' }}>
            Move the shipment. <span style={{ color: C.brand2 }}>Never the payment.</span>
          </div>
        </div>
        <Caption>The request looks legitimate. The second change is the one that costs you.</Caption>
      </Verse>
    </Backdrop>
  );
};

export const S02_Gap = ({ dur, audio }) => {
  const f = useCurrentFrame();
  const cols = [
    { title: 'What agents can do now', tone: C.brand2, items: ['Log in', 'Read the screen', 'Click, type, submit', 'Repeat for hours'] },
    { title: 'What has to be bounded', tone: C.ok, items: ['Which record', 'Which field', 'Which value', 'Which version — and proof'] },
  ];
  const gap = clamp01((f - 150) / 20);
  return (
    <Backdrop>
      <Grid />
      <Verse frame={f} dur={dur} audio={audio}>
        <Kicker>The gap</Kicker>
        <Headline size={62} width={1400}>
          Power is not the hard part. <span style={{ color: C.brand2 }}>Bounding it is.</span>
        </Headline>
        <div style={{ display: 'flex', gap: 46, marginTop: 54, alignItems: 'stretch' }}>
          {cols.map((col, ci) => (
            <Panel key={col.title} style={{ flex: 1, padding: 32 }} tone={ci === 1 ? '#101A28' : C.panel}>
              <div style={{ fontSize: 22, color: col.tone, fontWeight: 600, marginBottom: 22 }}>{col.title}</div>
              {col.items.map((item, i) => (
                <div key={item} style={{ ...rise(f, 40 + ci * 40 + i * 22), fontSize: 30, color: C.dim, padding: '10px 0', borderBottom: i < col.items.length - 1 ? `1px solid ${C.line}55` : 'none' }}>
                  {item}
                </div>
              ))}
            </Panel>
          ))}
          <div style={{ width: 190, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div
              style={{
                opacity: gap,
                transform: `scale(${0.9 + gap * 0.1})`,
                textAlign: 'center',
                fontFamily: C.mono,
                fontSize: 26,
                color: C.warn,
                border: `2px dashed ${C.warn}77`,
                borderRadius: 16,
                padding: '22px 16px',
                background: '#1E1A0E66',
              }}
            >
              the
              <br />
              middle
            </div>
          </div>
        </div>
        <Caption>Capability without a boundary is just risk with a nicer interface.</Caption>
      </Verse>
    </Backdrop>
  );
};

export const S03_Intro = ({ dur, audio }) => {
  const f = useCurrentFrame();
  const pillars = [
    { k: '01', t: 'Contract first', d: 'What may change is stated before anything moves.' },
    { k: '02', t: 'Bounded action', d: 'The model proposes. The runtime decides.' },
    { k: '03', t: 'Independent read-back', d: 'A second identity checks what actually landed.' },
  ];
  return (
    <Backdrop tint="#6C5CE7">
      <Grid />
      <Verse frame={f} dur={dur} audio={audio}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, ...rise(f, 6) }}>
          <div style={{ width: 54, height: 54, borderRadius: 15, background: `linear-gradient(140deg, ${C.brand}, ${C.brand2})`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26, fontWeight: 700 }}>✳</div>
          <div style={{ fontSize: 40, fontWeight: 700, letterSpacing: '-0.02em' }}>ProofPilot</div>
        </div>
        <div style={{ marginTop: 40, ...rise(f, 22) }}>
          <Headline size={74} width={1280}>
            One bounded change.
            <br />
            <span style={{ color: C.brand2 }}>A receipt you can check.</span>
          </Headline>
        </div>
        <div style={{ display: 'flex', gap: 30, marginTop: 58 }}>
          {pillars.map((p, i) => (
            <Panel key={p.k} style={{ flex: 1, padding: 30, ...rise(f, 70 + i * 26) }}>
              <div style={{ fontFamily: C.mono, color: C.brand2, fontSize: 20, marginBottom: 14 }}>{p.k}</div>
              <div style={{ fontSize: 31, fontWeight: 650, marginBottom: 12 }}>{p.t}</div>
              <div style={{ fontSize: 22, color: C.dim, lineHeight: 1.5 }}>{p.d}</div>
            </Panel>
          ))}
        </div>
        <Caption>Contract → decision → bounded write → read-back → evidence.</Caption>
      </Verse>
    </Backdrop>
  );
};

export const S04_Contract = ({ dur, audio }) => {
  const f = useCurrentFrame();
  const approved = clamp01((f - 150) / 18);
  const tampered = clamp01((f - 300) / 18);
  const rows = [
    ['REQ-001', 'Harbor Parts', '12 Canal Road, Amsterdam'],
    ['REQ-002', 'Northstar Supply', '44 Foundry Lane, Rotterdam'],
    ['REQ-003', 'Atlas Components', '8 Dock Street, Utrecht'],
  ];
  return (
    <Backdrop>
      <Grid />
      <Verse frame={f} dur={dur} audio={audio}>
        <Kicker>Step one · the contract</Kicker>
        <Headline size={58} width={1200}>
          Say exactly what may change — <span style={{ color: C.brand2 }}>then sign that</span>.
        </Headline>
        <div style={{ display: 'flex', gap: 44, marginTop: 46 }}>
          <Panel style={{ flex: 1, padding: 26 }}>
            <div style={{ fontSize: 19, color: C.dimmer, marginBottom: 16, fontFamily: C.mono }}>request.csv</div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 20 }}>
              <thead>
                <tr style={{ color: C.dimmer, fontSize: 14, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  <th style={{ textAlign: 'left', padding: '8px 0' }}>Request</th>
                  <th style={{ textAlign: 'left' }}>Supplier</th>
                  <th style={{ textAlign: 'left' }}>Proposed address</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={r[0]} style={rise(f, 40 + i * 18)}>
                    <td style={{ padding: '12px 0', borderTop: `1px solid ${C.line}66`, fontFamily: C.mono, color: C.brand2 }}>{r[0]}</td>
                    <td style={{ padding: '12px 12px', borderTop: `1px solid ${C.line}66` }}>{r[1]}</td>
                    <td style={{ padding: '12px 0', borderTop: `1px solid ${C.line}66`, color: C.dim }}>{r[2]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
          <Panel style={{ width: 500, padding: 30 }}>
            <div style={{ fontSize: 22, fontWeight: 650, marginBottom: 18 }}>Proposed contract</div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
              <Chip>field: shipping_address</Chip>
              <Chip>rows: 3</Chip>
              <Chip tone={C.bad} bg="#2A1218">bank: denied</Chip>
            </div>
            <div style={{ fontFamily: C.mono, fontSize: 17, color: C.dim, marginBottom: 8 }}>contract hash</div>
            <div style={{ fontFamily: C.mono, fontSize: 26, color: tampered ? C.bad : C.ink, background: '#0B1020', border: `1px solid ${C.line}`, borderRadius: 10, padding: '14px 16px' }}>
              {tampered ? 'a91f77de…' : '0056bf6c…'}
            </div>
            <div
              style={{
                marginTop: 22,
                padding: '15px 0',
                textAlign: 'center',
                borderRadius: 11,
                fontSize: 22,
                fontWeight: 600,
                background: approved && !tampered ? `linear-gradient(120deg, ${C.ok}, #23b78f)` : '#10162a',
                color: approved && !tampered ? '#04160F' : C.dimmer,
                border: `1px solid ${C.line}`,
                opacity: rise(f, 130).opacity,
              }}
            >
              {tampered ? 'Approval no longer applies' : approved ? 'Approved · bound to this hash' : 'Approve exact contract'}
            </div>
            <div style={{ marginTop: 16, fontSize: 19, color: tampered ? C.bad : C.dimmer, opacity: tampered ? 1 : 0.75 }}>
              {tampered ? 'One character changed → the approval expires.' : 'Change a character and the binding dies with it.'}
            </div>
          </Panel>
        </div>
        <Caption>Approval is attached to the contract, not to the conversation.</Caption>
      </Verse>
    </Backdrop>
  );
};
