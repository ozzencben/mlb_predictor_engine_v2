import React, { useState, useMemo } from 'react';
import SportsbookLogo from './SportsbookLogo';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmt1 = (v) => (v != null ? Number(v).toFixed(1) : '—');
const fmt2 = (v) => (v != null ? Number(v).toFixed(2) : '—');

/** American-odds or decimal odds → display string */
const fmtOdds = (v) => {
  if (!v || v === 0) return '—';
  const n = Number(v);
  if (isNaN(n)) return '—';
  if (Math.abs(n) >= 100) return n > 0 ? `+${n}` : `${n}`; // American
  return n.toFixed(2); // Decimal
};

/** outs → "5.2 IP" style label (baseball notation) */
const outsToIP = (outs) => {
  if (outs == null) return '—';
  const full = Math.floor(outs / 3);
  const rem = Math.round(outs % 3);
  return rem === 0 ? `${full}.0 IP` : `${full}.${rem} IP`;
};

/** Given an edge percent string/number, return a "heat" level */
const edgeHeat = (edge) => {
  const e = Number(edge) || 0;
  if (e >= 10) return 'hot';
  if (e >= 5) return 'warm';
  return 'none';
};

// ─── Sub-components ───────────────────────────────────────────────────────────

/** Glowing OVER / UNDER / PASS badge */
const PickBadge = ({ choice, edge }) => {
  if (choice === 'OVER') {
    const heat = edgeHeat(edge);
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-black uppercase tracking-wider
          bg-emerald-500/10 border text-emerald-400
          ${heat === 'hot' ? 'border-emerald-400/60 shadow-[0_0_10px_rgba(16,185,129,0.35)]' : 'border-emerald-500/30'}`}
      >
        ▲ OVER {edge > 0 && <span className="text-emerald-300 font-extrabold">+{edge}%</span>}
      </span>
    );
  }
  if (choice === 'UNDER') {
    const heat = edgeHeat(edge);
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-black uppercase tracking-wider
          bg-rose-500/10 border text-rose-400
          ${heat === 'hot' ? 'border-rose-400/60 shadow-[0_0_10px_rgba(244,63,94,0.35)]' : 'border-rose-500/30'}`}
      >
        ▼ UNDER {edge > 0 && <span className="text-rose-300 font-extrabold">+{edge}%</span>}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-lg text-[9px] font-bold uppercase tracking-wider bg-slate-800/40 border border-slate-700/30 text-slate-500">
      PASS
    </span>
  );
};

/** Thin progress bar comparing model projection vs book line */
const PropBar = ({ label, projVal, lineVal, color }) => {
  if (projVal == null) return null;
  const proj = Number(projVal);
  const line = lineVal != null ? Number(lineVal) : null;

  // Calculate bar fill: proj as % of a reasonable max
  const maxVal = line != null ? Math.max(proj, line) * 1.3 : proj * 1.3;
  const projPct = Math.min(100, (proj / maxVal) * 100);
  const linePct = line != null ? Math.min(100, (line / maxVal) * 100) : null;

  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span className="text-[9px] text-slate-500 font-black uppercase tracking-wider">{label}</span>
        <div className="flex items-center gap-2">
          {line != null && (
            <span className="text-[9px] text-slate-400 font-bold">
              Line <span className="text-white font-black">{line}</span>
            </span>
          )}
          <span className="text-[9px] text-slate-500 font-bold">
            Proj <span style={{ color }} className="font-black">{fmt1(proj)}</span>
          </span>
        </div>
      </div>
      <div className="relative h-1.5 bg-slate-800/60 rounded-full overflow-hidden">
        {/* Model projection bar */}
        <div
          className="absolute top-0 left-0 h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${projPct}%`, backgroundColor: color, opacity: 0.7 }}
        />
        {/* Book line indicator */}
        {linePct != null && (
          <div
            className="absolute top-0 h-full w-[2px] bg-white/50 rounded-full"
            style={{ left: `${linePct}%` }}
          />
        )}
      </div>
    </div>
  );
};

/** Odds row: shows over / under odds with book logo */
const OddsRow = ({ overOdds, underOdds, book }) => {
  if (!overOdds && !underOdds) return null;
  return (
    <div className="flex items-center justify-between pt-1">
      <div className="flex items-center gap-1.5">
        <SportsbookLogo bookmaker={book} size="xs" />
        <span className="text-[9px] text-slate-500 font-bold uppercase tracking-wider">{book || 'Book'}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-[9px] font-black text-emerald-400/80">
          OVR {fmtOdds(overOdds)}
        </span>
        <span className="text-[9px] font-black text-rose-400/80">
          UND {fmtOdds(underOdds)}
        </span>
      </div>
    </div>
  );
};

// ─── Main Prop Section inside a card ──────────────────────────────────────────

const PropSection = ({ icon, label, projVal, projLabel, lineVal, color, choice, edge, overOdds, underOdds, book }) => {
  const hasLine = lineVal != null;
  const hasEdge = choice !== 'PASS';

  return (
    <div
      className={`rounded-xl p-3 space-y-2.5 border transition-all duration-300
        ${hasEdge
          ? choice === 'OVER'
            ? 'bg-emerald-950/20 border-emerald-500/20'
            : 'bg-rose-950/20 border-rose-500/20'
          : 'bg-slate-950/30 border-slate-800/50'
        }`}
    >
      {/* Header row: label + badge */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-slate-400 font-black uppercase tracking-wider flex items-center gap-1">
          {icon} {label}
        </span>
        <PickBadge choice={choice} edge={edge} />
      </div>

      {/* Progress bar */}
      <PropBar
        label={projLabel}
        projVal={projVal}
        lineVal={hasLine ? lineVal : null}
        color={color}
      />

      {/* Odds row */}
      {hasLine && (
        <OddsRow overOdds={overOdds} underOdds={underOdds} book={book} />
      )}

      {!hasLine && (
        <p className="text-[9px] text-slate-600 font-bold">No book line available</p>
      )}
    </div>
  );
};

// ─── Single Pitcher Card ───────────────────────────────────────────────────────

const PitcherCard = ({ p }) => {
  const hasKEdge = p.k_choice !== 'PASS';
  const hasOutsEdge = p.outs_choice !== 'PASS';
  const hasAnyEdge = hasKEdge || hasOutsEdge;

  // Determine top-edge type for border glow
  const borderClass = hasAnyEdge
    ? 'border-indigo-500/25 shadow-[0_0_20px_rgba(99,102,241,0.06)]'
    : 'border-slate-800/70';

  return (
    <div
      className={`relative bg-slate-900/50 backdrop-blur-sm border rounded-2xl overflow-hidden transition-all duration-300 ${borderClass}`}
    >
      {/* Edge accent bar at top */}
      <div
        className={`absolute top-0 left-0 right-0 h-[2px] ${
          hasAnyEdge
            ? 'bg-gradient-to-r from-cyan-500/60 via-indigo-500/60 to-purple-500/60'
            : 'bg-slate-800/40'
        }`}
      />

      {/* ── Pitcher Header (compact) ── */}
      <div className="px-4 pt-4 pb-3 flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {/* Name + Hand badge */}
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-extrabold text-white text-sm tracking-wide leading-tight truncate">
              {p.pitcher}
            </h3>
            <span className="shrink-0 px-1.5 py-0.5 bg-slate-800 text-slate-300 border border-slate-700/50 rounded text-[9px] font-black uppercase tracking-wider">
              {p.throws}HP
            </span>
          </div>
          {/* Matchup */}
          <p className="mt-0.5 text-[11px] font-bold text-slate-400 tracking-wide">
            <span className="text-slate-200 font-black">{p.team}</span>
            <span className="text-slate-600 mx-1">vs</span>
            <span className="text-slate-300">{p.opponent}</span>
          </p>
        </div>

        {/* Edge summary pill (if any edge) */}
        {hasAnyEdge && (
          <div className="shrink-0 px-2.5 py-1 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center gap-1">
            <span className="text-indigo-400 text-[9px] font-black uppercase tracking-wider">EDGE</span>
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          </div>
        )}
      </div>

      {/* ── Props Grid ── */}
      <div className="px-3 pb-3 grid grid-cols-1 gap-2.5">
        {/* Strikeouts */}
        <PropSection
          icon="🎯"
          label="Strikeouts (K)"
          projVal={p.proj_k}
          projLabel="Projected Strikeouts"
          lineVal={p.k_line}
          color="#22d3ee"
          choice={p.k_choice}
          edge={p.k_edge}
          overOdds={p.k_over_odds}
          underOdds={p.k_under_odds}
          book={p.k_book}
        />

        {/* Total Outs */}
        <PropSection
          icon="⚡"
          label={`Total Outs — ${p.proj_outs != null ? outsToIP(p.proj_outs) : '—'}`}
          projVal={p.proj_outs}
          projLabel="Projected Outs"
          lineVal={p.outs_line}
          color="#818cf8"
          choice={p.outs_choice}
          edge={p.outs_edge}
          overOdds={p.outs_over_odds}
          underOdds={p.outs_under_odds}
          book={p.outs_book}
        />
      </div>
    </div>
  );
};

// ─── Main Component ────────────────────────────────────────────────────────────

function PitcherProjections({ pitcherProjections = [] }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [handFilter, setHandFilter] = useState('ALL');
  const [edgesOnly, setEdgesOnly] = useState(false);
  const [sortBy, setSortBy] = useState('edge'); // 'edge' | 'k' | 'outs'

  const filteredSorted = useMemo(() => {
    let list = pitcherProjections.filter((p) => {
      const q = searchTerm.toLowerCase();
      const matchSearch =
        !q ||
        (p.pitcher || '').toLowerCase().includes(q) ||
        (p.team || '').toLowerCase().includes(q) ||
        (p.opponent || '').toLowerCase().includes(q);

      const matchHand = handFilter === 'ALL' || p.throws === handFilter;

      const hasEdge = p.k_choice !== 'PASS' || p.outs_choice !== 'PASS';
      const matchEdge = !edgesOnly || hasEdge;

      return matchSearch && matchHand && matchEdge;
    });

    // Sort
    list = [...list].sort((a, b) => {
      if (sortBy === 'k') return (b.proj_k || 0) - (a.proj_k || 0);
      if (sortBy === 'outs') return (b.proj_outs || 0) - (a.proj_outs || 0);
      // 'edge': prioritize cards with picks
      const aEdge = Math.max(a.k_edge || 0, a.outs_edge || 0);
      const bEdge = Math.max(b.k_edge || 0, b.outs_edge || 0);
      return bEdge - aEdge;
    });

    return list;
  }, [pitcherProjections, searchTerm, handFilter, edgesOnly, sortBy]);

  // Summary stats
  const totalWithEdge = pitcherProjections.filter(
    (p) => p.k_choice !== 'PASS' || p.outs_choice !== 'PASS'
  ).length;

  return (
    <div className="space-y-4">
      {/* ── Hero Header ── */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900/60 to-slate-900/30 border border-slate-800/70 rounded-2xl p-4 md:p-5 shadow-xl backdrop-blur-md">
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 via-indigo-500/5 to-purple-500/5 pointer-events-none" />
        <div className="absolute -right-8 -top-8 w-40 h-40 bg-indigo-500/8 rounded-full blur-3xl pointer-events-none" />

        <div className="relative flex flex-col gap-3">
          {/* Title row */}
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base md:text-lg font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-indigo-400 to-purple-400 uppercase tracking-widest">
                Pitcher Props Model
              </h2>
              <p className="text-slate-500 text-[10px] md:text-xs font-semibold mt-0.5 leading-relaxed max-w-lg">
                K% projected via CSW/SwStr adjustments vs league avg · Outs via xFIP × wRC+ regression · Edge = model prob − book implied prob
              </p>
            </div>
            <div className="shrink-0 flex items-center gap-1.5 px-2.5 py-1 bg-cyan-500/10 border border-cyan-500/20 rounded-xl">
              <span className="flex h-1.5 w-1.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-cyan-500" />
              </span>
              <span className="text-[9px] text-cyan-400 font-extrabold uppercase tracking-widest hidden sm:block">Live</span>
            </div>
          </div>

          {/* Summary pills */}
          {pitcherProjections.length > 0 && (
            <div className="flex flex-wrap gap-2">
              <div className="px-2.5 py-1 rounded-lg bg-slate-800/60 border border-slate-700/40 text-[10px] font-bold text-slate-300">
                <span className="text-white font-black">{pitcherProjections.length}</span> Pitchers
              </div>
              <div className="px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-bold text-indigo-300">
                <span className="text-white font-black">{totalWithEdge}</span> Edges Found
              </div>
              <div className="px-2.5 py-1 rounded-lg bg-slate-800/60 border border-slate-700/40 text-[10px] font-bold text-slate-400">
                Threshold ≥ 5%
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Filter + Sort Toolbar ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {/* Search */}
        <div className="relative col-span-2 sm:col-span-1">
          <input
            type="text"
            placeholder="Search pitcher, team…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full h-10 pl-8 pr-3 bg-slate-900/60 border border-slate-800 focus:border-cyan-500/50 rounded-xl text-[11px] font-bold text-white placeholder-slate-500 outline-none transition-all duration-300"
          />
          <span className="absolute left-2.5 top-2.5 text-slate-500 text-xs">🔍</span>
        </div>

        {/* Hand Filter */}
        <div className="flex p-1 bg-slate-900/60 border border-slate-800 rounded-xl h-10 col-span-1">
          {['ALL', 'R', 'L'].map((hand) => (
            <button
              key={hand}
              onClick={() => setHandFilter(hand)}
              className={`flex-1 rounded-lg text-[9px] font-black uppercase tracking-wider transition-all duration-200 ${
                handFilter === hand
                  ? 'bg-cyan-500/15 border border-cyan-500/30 text-cyan-400'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {hand === 'ALL' ? 'All' : `${hand}HP`}
            </button>
          ))}
        </div>

        {/* Sort */}
        <div className="flex p-1 bg-slate-900/60 border border-slate-800 rounded-xl h-10 col-span-1">
          {[
            { key: 'edge', label: 'Edge' },
            { key: 'k', label: 'K' },
            { key: 'outs', label: 'IP' },
          ].map((s) => (
            <button
              key={s.key}
              onClick={() => setSortBy(s.key)}
              className={`flex-1 rounded-lg text-[9px] font-black uppercase tracking-wider transition-all duration-200 ${
                sortBy === s.key
                  ? 'bg-indigo-500/15 border border-indigo-500/30 text-indigo-400'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Edges Only */}
        <button
          onClick={() => setEdgesOnly(!edgesOnly)}
          className={`flex items-center justify-center gap-1.5 h-10 px-3 border rounded-xl transition-all duration-300 text-[9px] font-black uppercase tracking-wider col-span-2 sm:col-span-1 ${
            edgesOnly
              ? 'bg-indigo-500/15 border-indigo-500/40 text-indigo-400 shadow-[0_0_12px_rgba(99,102,241,0.15)]'
              : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
          }`}
        >
          <span className="text-sm">🔥</span>
          <span>Edges Only</span>
        </button>
      </div>

      {/* ── Cards ── */}
      {filteredSorted.length === 0 ? (
        <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-2xl p-10 text-center">
          <span className="text-3xl block mb-3">⚾</span>
          <h4 className="text-sm font-black text-white uppercase tracking-wider mb-1">No Projections Match</h4>
          <p className="text-slate-500 text-xs font-semibold max-w-xs mx-auto">
            Adjust filters or wait for game data to populate.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {filteredSorted.map((p, idx) => (
            <PitcherCard key={`pp-${p.pitcher}-${idx}`} p={p} />
          ))}
        </div>
      )}

      {/* Footer note */}
      {filteredSorted.length > 0 && (
        <p className="text-center text-[10px] text-slate-600 font-semibold pb-2">
          Edge = Model probability − Book implied probability · Threshold ≥ 5%
        </p>
      )}
    </div>
  );
}

export default PitcherProjections;
