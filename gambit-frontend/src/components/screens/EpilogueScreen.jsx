// src/components/screens/EpilogueScreen.jsx
// ─────────────────────────────────────────────────────────────────────────────
// MOCK DATA BLOCK — replace with live game resolution payload from backend
// ─────────────────────────────────────────────────────────────────────────────

// ── Mock: The Ending Classification ──────────────────────────
const MOCK_ENDING = {
  id: 'ENDING_03',
  title: 'The Hollow Accord',
  classification: 'Divergent',          // 'Canonical' | 'Near-Canonical' | 'Divergent' | 'Rupture'
  divergenceScore: 74,                  // 0 = identical to canon, 100 = complete rupture
  episodeTitle: 'Episode I — The Regent Rebellion',
  location: 'Empire Bay Hotel, Suite 412',
  date: '14 August 1995 · 03:47',
};

// ── Mock: The Epilogue Narration ──────────────────────────────
// What actually happened in this session
const MOCK_NARRATION_BEATS = [
  {
    type: 'environment',
    text: 'By the time the corridor lights returned, three of the four people in Suite 412 had already decided. The fourth — the one everyone had underestimated — had decided first.',
  },
  {
    type: 'environment',
    text: 'Govardhan Naidu left the hotel at dawn through the service entrance. He did not resign. He did not declare. He simply stopped returning calls, and in the silence that followed, the faction understood that the compact was broken.',
  },
  {
    type: 'speech',
    speaker: 'Raghava Rao',
    text: 'There was a moment — I saw it in his face — when he was still persuadable. That moment passed. And I let it.',
  },
  {
    type: 'environment',
    text: 'The press never reported what happened inside the suite. What they reported, three days later, was the result: a party congress that produced no resolution, a patriarch who appeared briefly and said nothing of substance, and an unsigned document that would be described for years afterward as "the paper that changed everything without saying anything at all."',
  },
];

// ── Mock: The Canonical Record ────────────────────────────────
// What the "real" historical ending was
const MOCK_CANONICAL = {
  title: 'The Regent\'s Compact',
  summary: 'In the canonical record, Govardhan Naidu signs the internal accord at 2:15 AM. Raghava Rao retains the public leadership position with Naidu\'s legislative backing. The crisis is contained. The party fracture is papered over for eleven months before resurfacing in a different, more permanent form.',
  verdict: 'Your session departed from the historical record. The accord was never signed. What followed was slower and less decisive — and in some ways, more honest.',
};

// ── Mock: Individual Role Verdicts ────────────────────────────
const MOCK_VERDICTS = [
  {
    roleKey: 'raghava_rao',
    name: 'Raghava Rao',
    analogue: 'Patriarch · Mass Leader',
    outcome: 'Survived',           // 'Survived' | 'Compromised' | 'Fell' | 'Defected'
    outcomeDetail: 'Retained symbolic authority. Lost operational control. The crowd still came when called, but the party had learned to route around him.',
    secretAchieved: false,
    secretLabel: 'Preserve legacy intact',
    playerName: 'Arjun Reddy',
  },
  {
    roleKey: 'govardhan_naidu',
    name: 'Govardhan Naidu',
    analogue: 'Strategist · Institutional Operator',
    outcome: 'Defected',
    outcomeDetail: 'Walked out of the accord negotiation. Did not cross the floor publicly, but withdrew legislative cooperation. The faction became ungovernable within weeks.',
    secretAchieved: true,
    secretLabel: 'Retain justification for the necessary',
    playerName: 'Kavitha Rao',
  },
  {
    roleKey: 'saraswathi',
    name: 'Saraswathi',
    analogue: 'Influence Center · Queenmaker',
    outcome: 'Survived',
    outcomeDetail: 'The only person who left the suite with more than she entered. Her access survived the collapse of the compact — because she had positioned herself as indispensable to both sides.',
    secretAchieved: true,
    secretLabel: 'Remain viable regardless of outcome',
    playerName: 'You',
  },
  {
    roleKey: 'venkatadri',
    name: 'Venkatadri',
    analogue: 'Family Hinge · Moral Witness',
    outcome: 'Compromised',
    outcomeDetail: 'The mediation attempt failed. Was present for both the moment of possibility and the moment of its closing, and will carry the weight of that witnessing for a very long time.',
    secretAchieved: false,
    secretLabel: 'Prevent public fracture',
    playerName: 'Dhruv Menon',
  },
];

// ── Mock: Aftermath Headlines ─────────────────────────────────
const MOCK_AFTERMATH = [
  {
    dateline: 'Empire Bay Courier · 17 August 1995',
    headline: 'Congress Ends Without Resolution; Leadership Question Persists',
    body: 'The three-day session concluded with no binding vote. Senior figures departed without addressing the press.',
  },
  {
    dateline: 'The Political Observer · 22 August 1995',
    headline: 'Naidu Faction Goes Quiet — but Does Not Go Away',
    body: 'Legislative observers note an unusual pattern of absences and procedural delays consistent with coordinated withdrawal.',
  },
  {
    dateline: 'Deccan Wire Service · 4 September 1995',
    headline: '"The Paper" Surfaces: What the Unsigned Accord Would Have Said',
    body: 'A partial transcript has been leaked to three publications simultaneously. The authenticity has not been denied.',
  },
];

// ── Mock: Key Decision Moments ────────────────────────────────
const MOCK_KEY_MOMENTS = [
  { round: 2, decision: 'The envelope was opened in front of witnesses.', impact: 'high',   label: 'Pivotal' },
  { round: 4, decision: 'Mediation was attempted but not pursued to completion.',impact: 'low', label: 'Missed' },
  { round: 6, decision: 'Saraswathi broke the information deadlock unilaterally.', impact: 'high',  label: 'Decisive' },
  { round: 7, decision: 'Naidu was offered a final exit with dignity. He declined.', impact: 'high', label: 'Turning Point' },
];

// ─────────────────────────────────────────────────────────────────────────────
// END MOCK DATA BLOCK
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence, useInView } from 'framer-motion';
import { Button } from '../ui';

// ── Helpers ────────────────────────────────────────────────────────────────

const OUTCOME_STYLES = {
  Survived:    { color: 'var(--color-gold)',      label: 'Survived'    },
  Compromised: { color: 'var(--color-text-dim)',  label: 'Compromised' },
  Fell:        { color: 'var(--color-red-primary)', label: 'Fell'      },
  Defected:    { color: 'var(--color-red-dim)',   label: 'Defected'    },
};

const CLASSIFICATION_STYLES = {
  Canonical:       { color: 'var(--color-gold)',        bg: 'rgba(201,168,76,0.07)'  },
  'Near-Canonical':{ color: 'var(--color-gold-dim)',    bg: 'rgba(122,100,48,0.07)'  },
  Divergent:       { color: 'var(--color-text-dim)',    bg: 'rgba(138,128,112,0.07)' },
  Rupture:         { color: 'var(--color-red-primary)', bg: 'rgba(139,38,53,0.09)'   },
};

// Divergence meter — reads 0 (canonical) → 100 (total rupture)
const DivergenceMeter = ({ score }) => {
  const [displayed, setDisplayed] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setDisplayed(score), 600);
    return () => clearTimeout(t);
  }, [score]);

  const color =
    score >= 70 ? 'var(--color-text-dim)' :
    score >= 40 ? 'var(--color-gold-dim)' :
    'var(--color-gold)';

  return (
    <div>
      <div className="flex justify-between items-end mb-2">
        <span className="font-mono text-[8px] tracking-[0.4em] uppercase text-text-faint">
          Historical Divergence
        </span>
        <motion.span
          className="font-serif text-[26px] font-light"
          style={{ color }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
        >
          {displayed}
          <span className="text-[14px] text-text-faint font-sans ml-0.5">/100</span>
        </motion.span>
      </div>

      {/* Track */}
      <div className="relative h-[2px] w-full" style={{ background: 'var(--color-border-primary)' }}>
        {/* Canonical marker */}
        <div className="absolute top-1/2 -translate-y-1/2 w-px h-3"
          style={{ left: '0%', background: 'var(--color-gold)', opacity: 0.6 }}
        />
        <div className="absolute -top-5 font-mono text-[7px] tracking-wider text-gold opacity-60"
          style={{ left: '2px' }}>
          Canon
        </div>

        {/* Fill */}
        <div
          className="absolute left-0 top-0 h-full"
          style={{
            width: `${displayed}%`,
            background: color,
            transition: 'width 1.4s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        />

        {/* Rupture marker */}
        <div className="absolute top-1/2 -translate-y-1/2 w-px h-3"
          style={{ left: '100%', background: 'var(--color-red-primary)', opacity: 0.5 }}
        />
        <div className="absolute -top-5 font-mono text-[7px] tracking-wider"
          style={{ right: 0, color: 'var(--color-red-dim)', opacity: 0.6 }}>
          Rupture
        </div>
      </div>
    </div>
  );
};


// ── Fade-in-on-scroll block ───────────────────────────────────
const FadeIn = ({ children, delay = 0, className = '' }) => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-40px' });

  return (
    <motion.div
      ref={ref}
      className={className}
      initial={{ opacity: 0, y: 18 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.55, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
};


// ── Section divider ───────────────────────────────────────────
const SectionDivider = ({ label }) => (
  <div className="flex items-center gap-4 my-10">
    <div className="flex-1 h-px" style={{ background: 'var(--color-border-primary)' }} />
    <span className="font-mono text-[8px] tracking-[0.5em] uppercase"
      style={{ color: 'var(--color-text-faint)' }}>
      {label}
    </span>
    <div className="flex-1 h-px" style={{ background: 'var(--color-border-primary)' }} />
  </div>
);


// ── VerdictCard ───────────────────────────────────────────────
const VerdictCard = ({ verdict, delay, currentPlayerName }) => {
  const outcome = OUTCOME_STYLES[verdict.outcome] ?? OUTCOME_STYLES.Survived;
  const isYou = verdict.playerName === 'You' || verdict.playerName === currentPlayerName;

  return (
    <FadeIn delay={delay}>
      <div
        className="relative p-5 border"
        style={{
          borderColor: isYou ? 'rgba(201,168,76,0.4)' : 'var(--color-border-primary)',
          background: isYou ? 'rgba(201,168,76,0.03)' : 'var(--color-deep)',
          borderLeftWidth: isYou ? 3 : 1,
          borderLeftColor: isYou ? 'var(--color-gold)' : undefined,
        }}
      >
        {/* Top strip */}
        {isYou && (
          <div className="absolute top-0 left-0 right-0 h-px"
            style={{ background: 'linear-gradient(to right, var(--color-gold), transparent)' }}
          />
        )}

        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="font-mono text-[8px] tracking-[0.3em] uppercase mb-1"
              style={{ color: isYou ? 'var(--color-gold)' : 'var(--color-text-faint)' }}>
              {isYou ? 'Your Role' : verdict.playerName}
            </p>
            <h3 className="font-serif text-[17px] font-light" style={{ color: 'var(--color-text-primary)' }}>
              {verdict.name}
            </h3>
            <p className="font-mono text-[8px] tracking-[0.25em] uppercase mt-0.5"
              style={{ color: 'var(--color-gold-dim)' }}>
              {verdict.analogue}
            </p>
          </div>

          <span
            className="font-mono text-[9px] tracking-[0.3em] uppercase px-2.5 py-1 border mt-1"
            style={{ color: outcome.color, borderColor: outcome.color, opacity: 0.9 }}
          >
            {outcome.label}
          </span>
        </div>

        <p className="text-[12.5px] leading-relaxed mb-4"
          style={{ color: 'var(--color-text-dim)' }}>
          {verdict.outcomeDetail}
        </p>

        {/* Secret objective result */}
        <div className="flex items-center gap-2.5 pt-3 border-t"
          style={{ borderColor: 'var(--color-border-primary)' }}>
          <div className="w-1.5 h-1.5 flex-shrink-0 rotate-45"
            style={{ background: verdict.secretAchieved ? 'var(--color-gold)' : 'var(--color-text-faint)' }}
          />
          <p className="font-mono text-[8px] tracking-[0.2em] uppercase"
            style={{ color: verdict.secretAchieved ? 'var(--color-gold-dim)' : 'var(--color-text-faint)' }}>
            Secret objective: {verdict.secretAchieved ? 'Achieved' : 'Failed'} — {verdict.secretLabel}
          </p>
        </div>
      </div>
    </FadeIn>
  );
};


// ── Main EpilogueScreen ───────────────────────────────────────
export const EpilogueScreen = ({ result, currentPlayerName, onPlayAgain, onReturnToLobby }) => {
  const ending = result?.ending || MOCK_ENDING;
  const narrationBeats = result?.narration_beats?.length ? result.narration_beats : MOCK_NARRATION_BEATS;
  const canonical = result?.canonical || MOCK_CANONICAL;
  const verdicts = result?.verdicts?.length ? result.verdicts : MOCK_VERDICTS;
  const aftermath = result?.aftermath_headlines?.length ? result.aftermath_headlines : MOCK_AFTERMATH;
  const keyMoments = result?.key_moments?.length ? result.key_moments : MOCK_KEY_MOMENTS;
  const clsStyle = CLASSIFICATION_STYLES[ending.classification] ?? CLASSIFICATION_STYLES.Divergent;
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setRevealed(true), 200);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="w-screen min-h-screen overflow-y-auto overflow-x-hidden"
      style={{ background: 'var(--color-black)', scrollbarWidth: 'none' }}
    >
      {/* ── HERO — Ending reveal ────────────────────────────── */}
      <div className="relative flex flex-col items-center justify-center text-center px-6"
        style={{ minHeight: '100vh' }}>

        {/* Radial glow behind title */}
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 60% 40% at 50% 50%, rgba(201,168,76,0.05) 0%, transparent 70%)' }}
        />

        {/* Episode label */}
        <motion.p
          className="font-mono text-[9px] tracking-[0.55em] uppercase mb-6"
          style={{ color: 'var(--color-text-faint)' }}
          initial={{ opacity: 0 }} animate={{ opacity: revealed ? 1 : 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          {ending.episodeTitle}
        </motion.p>

        {/* Horizontal rule top */}
        <motion.div className="w-32 h-px mb-8"
          style={{ background: 'linear-gradient(to right, transparent, var(--color-gold-dim), transparent)' }}
          initial={{ scaleX: 0 }} animate={{ scaleX: revealed ? 1 : 0 }}
          transition={{ duration: 0.9, delay: 0.35, ease: [0.16, 1, 0.3, 1] }}
        />

        {/* Ending ID */}
        <motion.p
          className="font-mono text-[9px] tracking-[0.6em] uppercase mb-4"
          style={{ color: 'var(--color-gold-dim)' }}
          initial={{ opacity: 0 }} animate={{ opacity: revealed ? 1 : 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          {ending.id}
        </motion.p>

        {/* Ending Title */}
        <motion.h1
          className="font-serif font-light leading-none tracking-tight mb-5"
          style={{ fontSize: 'clamp(42px, 7vw, 80px)', color: 'var(--color-text-primary)' }}
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: revealed ? 1 : 0, y: revealed ? 0 : 20 }}
          transition={{ duration: 0.8, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          {ending.title}
        </motion.h1>

        {/* Classification badge */}
        <motion.div
          className="font-mono text-[9px] tracking-[0.45em] uppercase px-4 py-1.5 border mb-8"
          style={{ color: clsStyle.color, borderColor: clsStyle.color, background: clsStyle.bg }}
          initial={{ opacity: 0 }} animate={{ opacity: revealed ? 1 : 0 }}
          transition={{ duration: 0.5, delay: 0.85 }}
        >
          {ending.classification} Ending
        </motion.div>

        {/* Location / time stamp */}
        <motion.p
          className="font-mono text-[9px] tracking-[0.4em] uppercase"
          style={{ color: 'var(--color-text-faint)' }}
          initial={{ opacity: 0 }} animate={{ opacity: revealed ? 1 : 0 }}
          transition={{ duration: 0.5, delay: 1 }}
        >
          {ending.location} · {ending.date}
        </motion.p>

        {/* Scroll nudge */}
        <motion.div
          className="absolute bottom-10 flex flex-col items-center gap-2"
          initial={{ opacity: 0 }} animate={{ opacity: revealed ? 0.5 : 0 }}
          transition={{ delay: 1.4, duration: 0.5 }}
        >
          <p className="font-mono text-[8px] tracking-[0.45em] uppercase"
            style={{ color: 'var(--color-text-faint)' }}>
            Read the record
          </p>
          <motion.div
            className="w-px h-8"
            style={{ background: 'linear-gradient(to bottom, var(--color-border-secondary), transparent)' }}
            animate={{ scaleY: [0, 1, 0], originY: 0 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 1.5 }}
          />
        </motion.div>
      </div>


      {/* ── BODY — Full epilogue content ───────────────────── */}
      <div className="max-w-[820px] mx-auto px-6 pb-32">

        {/* ── Divergence Meter ─────────────────────────────── */}
        <FadeIn>
          <div className="pt-10 pb-8 border-b" style={{ borderColor: 'var(--color-border-primary)' }}>
            <DivergenceMeter score={ending.divergenceScore} />
          </div>
        </FadeIn>

        {/* ── What Happened — Narration ─────────────────────── */}
        <SectionDivider label="What Happened" />

        <div className="flex flex-col gap-7">
          {narrationBeats.map((beat, i) => (
            <FadeIn key={i} delay={i * 0.06}>
              {beat.type === 'environment' ? (
                <p className="font-serif text-[16.5px] italic font-light leading-[1.85]"
                  style={{ color: 'var(--color-text-dim)' }}>
                  {beat.text}
                </p>
              ) : (
                <div className="pl-5 border-l-2"
                  style={{ borderColor: 'rgba(122, 100, 48, 0.4)' }}>
                  <p className="font-mono text-[8.5px] tracking-[0.35em] uppercase mb-2"
                    style={{ color: 'var(--color-gold-dim)' }}>
                    {beat.speaker}
                  </p>
                  <p className="font-serif text-[17px] leading-relaxed"
                    style={{ color: 'var(--color-text-primary)' }}>
                    "{beat.text}"
                  </p>
                </div>
              )}
            </FadeIn>
          ))}
        </div>

        {/* ── The Canonical Record ─────────────────────────── */}
        <SectionDivider label="The Canonical Record" />

        <FadeIn>
          <div className="relative p-7 border"
            style={{ borderColor: 'var(--color-border-secondary)', background: 'var(--color-deep)' }}>
            <div className="absolute top-0 left-0 right-0 h-px"
              style={{ background: 'linear-gradient(to right, transparent, var(--color-border-secondary), transparent)' }}
            />

            <div className="flex items-start gap-5 mb-5">
              <div className="flex-shrink-0 mt-1">
                <div className="w-1.5 h-1.5 rotate-45" style={{ background: 'var(--color-gold-dim)' }} />
              </div>
              <div>
                <p className="font-mono text-[8px] tracking-[0.4em] uppercase mb-2"
                  style={{ color: 'var(--color-text-faint)' }}>
                  What History Recorded
                </p>
                <h3 className="font-serif text-[22px] font-light mb-4"
                  style={{ color: 'var(--color-text-primary)' }}>
                  {canonical.title}
                </h3>
                <p className="text-[13.5px] leading-[1.8]"
                  style={{ color: 'var(--color-text-dim)' }}>
                  {canonical.summary}
                </p>
              </div>
            </div>

            <div className="pl-6 pt-4 border-t" style={{ borderColor: 'var(--color-border-primary)' }}>
              <p className="font-serif text-[13.5px] italic"
                style={{ color: 'var(--color-text-faint)' }}>
                {canonical.verdict}
              </p>
            </div>
          </div>
        </FadeIn>

        {/* ── Key Moments ──────────────────────────────────── */}
        <SectionDivider label="Moments That Mattered" />

        <div className="flex flex-col gap-3">
          {keyMoments.map((m, i) => (
            <FadeIn key={i} delay={i * 0.07}>
              <div className="flex items-start gap-4 px-4 py-3.5 border"
                style={{ borderColor: 'var(--color-border-primary)', background: 'var(--color-deep)' }}>
                <span className="font-mono text-[8px] tracking-[0.3em] uppercase pt-0.5 flex-shrink-0"
                  style={{ color: 'var(--color-text-faint)', minWidth: 48 }}>
                  Rd. {m.round}
                </span>
                <p className="flex-1 text-[13px] leading-relaxed"
                  style={{ color: 'var(--color-text-dim)' }}>
                  {m.decision}
                </p>
                <span
                  className="flex-shrink-0 font-mono text-[8px] tracking-[0.25em] uppercase px-2 py-0.5 border"
                  style={{
                    color: m.impact === 'high' ? 'var(--color-gold)' : 'var(--color-text-faint)',
                    borderColor: m.impact === 'high' ? 'var(--color-gold-dim)' : 'var(--color-border-primary)',
                  }}
                >
                  {m.label}
                </span>
              </div>
            </FadeIn>
          ))}
        </div>

        {/* ── Role Verdicts ─────────────────────────────────── */}
        <SectionDivider label="Individual Reckoning" />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {verdicts.map((v, i) => (
            <VerdictCard key={v.roleKey || v.playerName} verdict={v} delay={i * 0.08} currentPlayerName={currentPlayerName} />
          ))}
        </div>

        {/* ── Aftermath Chronicle ───────────────────────────── */}
        <SectionDivider label="Aftermath" />

        {/* Masthead */}
        <FadeIn>
          <div className="border border-border-primary mb-0"
            style={{ background: 'var(--color-deep)' }}>
            <div className="text-center py-4 border-b"
              style={{ borderColor: 'var(--color-border-primary)' }}>
              <p className="font-serif text-[11px] italic tracking-widest"
                style={{ color: 'var(--color-text-faint)' }}>
                Historical Record · Post-Session Dispatch
              </p>
              <div className="flex items-center gap-2 justify-center mt-2">
                <div className="h-px w-16" style={{ background: 'var(--color-border-secondary)' }} />
                <div className="w-1 h-1 rotate-45 flex-shrink-0"
                  style={{ background: 'var(--color-gold-dim)', opacity: 0.6 }} />
                <div className="h-px w-8" style={{ background: 'var(--color-gold-dim)', opacity: 0.4 }} />
                <div className="w-1 h-1 rotate-45 flex-shrink-0"
                  style={{ background: 'var(--color-gold-dim)', opacity: 0.6 }} />
                <div className="h-px w-16" style={{ background: 'var(--color-border-secondary)' }} />
              </div>
            </div>

            {aftermath.map((item, i) => (
              <div key={i} className="px-6 py-5 border-b last:border-0"
                style={{ borderColor: 'var(--color-border-primary)' }}>
                <p className="font-mono text-[8px] tracking-[0.3em] uppercase mb-2"
                  style={{ color: 'var(--color-text-faint)' }}>
                  {item.dateline}
                </p>
                <p className="font-serif text-[15px] font-semibold leading-snug mb-2"
                  style={{ color: 'var(--color-text-primary)' }}>
                  {item.headline}
                </p>
                <p className="text-[12px] leading-relaxed"
                  style={{ color: 'var(--color-text-dim)' }}>
                  {item.body}
                </p>
              </div>
            ))}
          </div>
        </FadeIn>

        {/* ── Closing line ─────────────────────────────────── */}
        <FadeIn delay={0.1}>
          <div className="mt-12 text-center">
            <div className="flex items-center gap-4 mb-8">
              <div className="flex-1 h-px"
                style={{ background: 'linear-gradient(to right, transparent, var(--color-border-secondary))' }} />
              <div className="w-1.5 h-1.5 rotate-45 flex-shrink-0"
                style={{ background: 'var(--color-gold-dim)', opacity: 0.6 }} />
              <div className="flex-1 h-px"
                style={{ background: 'linear-gradient(to left, transparent, var(--color-border-secondary))' }} />
            </div>

            <p className="font-serif text-[19px] italic font-light leading-relaxed mb-2"
              style={{ color: 'var(--color-text-dim)' }}>
              "History does not record what might have been.
            </p>
            <p className="font-serif text-[19px] italic font-light leading-relaxed"
              style={{ color: 'var(--color-text-dim)' }}>
              Only what was — and what was allowed to happen."
            </p>
          </div>
        </FadeIn>

        {/* ── Actions ──────────────────────────────────────── */}
        <FadeIn delay={0.2}>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-14">
            <Button onClick={onPlayAgain} variant="primary" className="min-w-[200px]">
              Play Again
            </Button>
            <Button onClick={onReturnToLobby} variant="secondary" className="min-w-[200px]">
              Return to Lobby
            </Button>
          </div>

          <p className="text-center font-mono text-[8px] tracking-[0.35em] uppercase mt-5"
            style={{ color: 'var(--color-text-faint)' }}>
            Empire Bay Hotel · August 1995
          </p>
        </FadeIn>
      </div>
    </div>
  );
};
