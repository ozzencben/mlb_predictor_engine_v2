import React, { useState, useEffect, useCallback } from 'react';
import { useTennisPredictions } from '../hooks/useTennisPredictions';
import apiClient from '../api/client';

// ─────────────────────────────────────────────────────────────
//  Helper: American Odds formatı
// ─────────────────────────────────────────────────────────────
function formatOdds(decimalOdds) {
    if (!decimalOdds || decimalOdds <= 1.0) return null;
    const dec = parseFloat(decimalOdds);
    if (dec >= 2.0) return `+${Math.round((dec - 1.0) * 100)}`;
    return `${Math.round(-100.0 / (dec - 1.0))}`;
}

// ─────────────────────────────────────────────────────────────
//  Helper: Zemin renk/stil
// ─────────────────────────────────────────────────────────────
function getSurfaceStyles(surface) {
    const s = (surface || '').toLowerCase();
    if (s.includes('grass')) return {
        bg: 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400',
        dot: 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]',
        label: 'Grass',
    };
    if (s.includes('clay')) return {
        bg: 'bg-amber-500/10 border-amber-500/25 text-amber-400',
        dot: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]',
        label: 'Clay',
    };
    return {
        bg: 'bg-blue-500/10 border-blue-500/25 text-blue-400',
        dot: 'bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.5)]',
        label: 'Hard',
    };
}

// ─────────────────────────────────────────────────────────────
//  Helper: Oyuncu Baş Harfleri (Avatar için)
// ─────────────────────────────────────────────────────────────
function getPlayerInitials(name) {
    if (!name) return '??';
    const clean = name.replace(/\./g, '').trim();
    const parts = clean.split(' ');
    if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return clean.slice(0, 2).toUpperCase();
}

// ─────────────────────────────────────────────────────────────
//  Helper: renderAiInsight
// ─────────────────────────────────────────────────────────────
function renderAiInsight(text) {
    if (!text) return null;

    // Split by lines and filter bullet points
    const bullets = text.split('\n')
        .map(l => l.trim())
        .filter(l => l.startsWith('-') || l.startsWith('*'));

    if (bullets.length === 3) {
        const titles = ["Surface & ELO Edge", "Physical & Fatigue Factor", "The Betting Angle"];
        const icons = ["🏟️", "🔋", "🎯"];
        return (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 mt-1">
                {bullets.map((b, idx) => {
                    const content = b.replace(/^[-*]\s*/, '');
                    return (
                        <div key={idx} className="bg-slate-950/50 border border-slate-900/60 rounded-2xl p-3.5 space-y-1 transition-all duration-300 hover:border-slate-850">
                            <div className="flex items-center gap-1.5">
                                <span className="text-xs">{icons[idx]}</span>
                                <span className="text-[8px] font-black uppercase tracking-wider text-slate-500">{titles[idx]}</span>
                            </div>
                            <p className="text-[10px] text-slate-300 leading-relaxed font-semibold">{content}</p>
                        </div>
                    );
                })}
            </div>
        );
    }

    return (
        <div className="bg-slate-950/50 border border-slate-900/60 rounded-2xl p-4 text-[10px] text-slate-300 leading-relaxed font-semibold whitespace-pre-line">
            {text}
        </div>
    );
}

// ─────────────────────────────────────────────────────────────
//  Helper: StatsComparison
// ─────────────────────────────────────────────────────────────
function StatsComparison({ p1, p2 }) {
    if (!p1 || !p2) return null;

    const rows = [
        { label: 'World Ranking', p1Val: p1.rank, p2Val: p2.rank, format: v => `#${v}`, higherIsBetter: false, icon: '🏅' },
        { label: 'Surface ELO Rating', p1Val: p1.elo, p2Val: p2.elo, format: v => Math.round(v), higherIsBetter: true, icon: '🧠' },
        { label: 'Court DNA (Surface %)', p1Val: p1.surface_rate * 100, p2Val: p2.surface_rate * 100, format: v => `${v.toFixed(1)}%`, higherIsBetter: true, icon: '🏟️' },
        { label: 'Form Momentum', p1Val: p1.momentum * 100, p2Val: p2.momentum * 100, format: v => `${v.toFixed(1)}%`, higherIsBetter: true, icon: '📈' },
        { label: 'Fatigue (3-Game Sets)', p1Val: p1.fatigue, p2Val: p2.fatigue, format: v => `${v} Sets`, higherIsBetter: false, icon: '🔋' },
        { label: 'Set Dominance', p1Val: p1.set_dominance * 100, p2Val: p2.set_dominance * 100, format: v => `${v.toFixed(1)}%`, higherIsBetter: true, icon: '⚡' },
        { label: 'Game Dominance', p1Val: p1.game_dominance * 100, p2Val: p2.game_dominance * 100, format: v => `${v.toFixed(1)}%`, higherIsBetter: true, icon: '🎮' },
        { label: 'Recovery Window', p1Val: p1.rest_days, p2Val: p2.rest_days, format: v => `${v} Days`, higherIsBetter: true, icon: '💤' },
        { label: 'Clutch Deciding Set %', p1Val: p1.clutch_win_rate, p2Val: p2.clutch_win_rate, format: v => `${v.toFixed(1)}%`, higherIsBetter: true, icon: '🔥' },
        { label: 'Straight Sets Sweep %', p1Val: p1.straight_sets_rate, p2Val: p2.straight_sets_rate, format: v => `${v.toFixed(1)}%`, higherIsBetter: true, icon: '🧹' }
    ];

    return (
        <div className="bg-slate-950/40 border border-slate-900/80 rounded-2xl p-4 space-y-3 shadow-inner">
            <h5 className="text-[9px] font-black uppercase tracking-widest text-slate-500 text-center mb-1">🔍 Röntgen Sabermetrics Matchup</h5>
            <div className="space-y-2.5">
                {rows.map((row, idx) => {
                    let p1Highlight = false;
                    let p2Highlight = false;

                    if (row.p1Val !== row.p2Val) {
                        if (row.higherIsBetter) {
                            p1Highlight = row.p1Val > row.p2Val;
                            p2Highlight = row.p2Val > row.p1Val;
                        } else {
                            p1Highlight = row.p1Val < row.p2Val;
                            p2Highlight = row.p2Val < row.p1Val;
                        }
                    }

                    return (
                        <div key={idx} className="flex items-center justify-between text-[10px] gap-2 border-b border-slate-900/40 pb-2 last:border-0 last:pb-0 select-none">
                            {/* Player 1 value */}
                            <div className="w-[30%] text-left font-black">
                                <span className={p1Highlight ? 'text-indigo-400 font-extrabold drop-shadow-[0_0_8px_rgba(129,140,248,0.2)]' : 'text-slate-400 font-semibold'}>
                                    {row.format(row.p1Val)}
                                </span>
                            </div>

                            {/* Metric Label */}
                            <div className="w-[40%] text-center flex flex-col items-center">
                                <span className="text-[7.5px] text-slate-500 font-black uppercase tracking-wider text-center block">
                                    {row.icon} {row.label}
                                </span>
                            </div>

                            {/* Player 2 value */}
                            <div className="w-[30%] text-right font-black">
                                <span className={p2Highlight ? 'text-indigo-400 font-extrabold drop-shadow-[0_0_8px_rgba(129,140,248,0.2)]' : 'text-slate-400 font-semibold'}>
                                    {row.format(row.p2Val)}
                                </span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────
//  Helper: Recent Form Badges (Son 5 Maç W/L)
// ─────────────────────────────────────────────────────────────
function RecentFormBadges({ recentForm }) {
    if (!recentForm || recentForm.length === 0) return null;
    return (
        <div className="flex items-center gap-1 mt-1">
            {recentForm.map((m, i) => (
                <div key={i} className="group/form relative">
                    <span
                        className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[8px] font-black border transition-all duration-200
                            ${m.result === 'W'
                                ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30 group-hover/form:shadow-[0_0_8px_rgba(52,211,153,0.3)]'
                                : 'bg-rose-950/60 text-rose-400 border-rose-500/30 group-hover/form:shadow-[0_0_8px_rgba(244,63,94,0.3)]'
                            }`}
                    >
                        {m.result}
                    </span>
                    {/* Tooltip */}
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-[8px] text-slate-300 font-bold whitespace-nowrap opacity-0 invisible group-hover/form:opacity-100 group-hover/form:visible transition-all duration-200 z-50 shadow-xl pointer-events-none">
                        <div className="font-black text-white">{m.result === 'W' ? '✅' : '❌'} vs {m.opponent}</div>
                        <div className="text-slate-400 mt-0.5">{m.score} · {m.surface} · {m.tournament}</div>
                        <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-slate-800" />
                    </div>
                </div>
            ))}
        </div>
    );
}

// ─────────────────────────────────────────────────────────────
//  Helper: H2H Summary
// ─────────────────────────────────────────────────────────────
function H2HSummary({ h2h, p1Name, p2Name }) {
    if (!h2h || h2h.total_matches === 0) return null;
    return (
        <div className="bg-slate-950/50 border border-slate-900/60 rounded-2xl p-3.5 space-y-2.5">
            <div className="flex items-center justify-between">
                <span className="text-[7.5px] font-black uppercase tracking-widest text-slate-500">🤝 Head-to-Head History</span>
                <span className="text-[8px] font-black text-slate-600 bg-slate-950/60 border border-slate-900 px-2 py-0.5 rounded">
                    {h2h.total_matches} Match{h2h.total_matches > 1 ? 'es' : ''}
                </span>
            </div>
            {/* Score Summary */}
            <div className="flex items-center justify-center gap-4">
                <div className="text-center">
                    <span className={`text-lg font-black ${h2h.p1_wins >= h2h.p2_wins ? 'text-indigo-400' : 'text-slate-500'}`}>{h2h.p1_wins}</span>
                    <span className="text-[8px] text-slate-500 font-bold block truncate max-w-[80px] sm:max-w-[120px]">{p1Name}</span>
                </div>
                <span className="text-[10px] text-slate-600 font-black">—</span>
                <div className="text-center">
                    <span className={`text-lg font-black ${h2h.p2_wins >= h2h.p1_wins ? 'text-indigo-400' : 'text-slate-500'}`}>{h2h.p2_wins}</span>
                    <span className="text-[8px] text-slate-500 font-bold block truncate max-w-[80px] sm:max-w-[120px]">{p2Name}</span>
                </div>
            </div>
            {/* Recent H2H Matches */}
            {h2h.matches && h2h.matches.length > 0 && (
                <div className="space-y-1.5 pt-1 border-t border-slate-900/50">
                    {h2h.matches.map((m, i) => (
                        <div key={i} className="flex items-center justify-between text-[9px] gap-2">
                            <span className={`font-black truncate max-w-[100px] sm:max-w-[140px] ${m.winner === p1Name ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {m.winner === p1Name ? '✅' : '❌'} {m.winner}
                            </span>
                            <span className="text-slate-600 font-bold flex-shrink-0">{m.score}</span>
                            <span className="text-slate-500 font-bold truncate max-w-[80px] sm:max-w-[120px] text-right">{m.tournament} · {m.surface}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ─────────────────────────────────────────────────────────────
//  Helper: Recent Form History
// ─────────────────────────────────────────────────────────────
function RecentFormHistory({ p1Name, p1Form, p2Name, p2Form }) {
    if ((!p1Form || p1Form.length === 0) && (!p2Form || p2Form.length === 0)) return null;

    return (
        <div className="bg-slate-950/50 border border-slate-900/60 rounded-2xl p-3.5 space-y-2.5">
            <span className="text-[7.5px] font-black uppercase tracking-widest text-slate-500 block">📊 Recent Matches &amp; Form (Last 5)</span>
            <div className="grid grid-cols-2 gap-4">
                {/* P1 Form */}
                <div className="space-y-2">
                    <span className="text-[9px] font-black uppercase text-indigo-400 block truncate">{p1Name}</span>
                    <div className="space-y-1.5">
                        {p1Form && p1Form.slice(0, 5).map((match, idx) => (
                            <div key={idx} className="bg-slate-900/40 border border-slate-900/60 p-2 rounded-xl text-[9px] leading-tight space-y-0.5">
                                <div className="flex justify-between items-center gap-1">
                                    <span className="text-white font-black truncate max-w-[80px]">{match.tournament.split('(')[0].trim()}</span>
                                    <span className={`px-1 rounded font-black text-[8px] ${match.result === 'W' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                                        {match.result}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center text-slate-500">
                                    <span className="truncate max-w-[70px]">vs {match.opponent}</span>
                                    <span>{match.score}</span>
                                </div>
                            </div>
                        ))}
                        {(!p1Form || p1Form.length === 0) && (
                            <span className="text-[9px] text-slate-600 font-bold block">No recent matches</span>
                        )}
                    </div>
                </div>

                {/* P2 Form */}
                <div className="space-y-2">
                    <span className="text-[9px] font-black uppercase text-indigo-400 block truncate">{p2Name}</span>
                    <div className="space-y-1.5">
                        {p2Form && p2Form.slice(0, 5).map((match, idx) => (
                            <div key={idx} className="bg-slate-900/40 border border-slate-900/60 p-2 rounded-xl text-[9px] leading-tight space-y-0.5">
                                <div className="flex justify-between items-center gap-1">
                                    <span className="text-white font-black truncate max-w-[80px]">{match.tournament.split('(')[0].trim()}</span>
                                    <span className={`px-1 rounded font-black text-[8px] ${match.result === 'W' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                                        {match.result}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center text-slate-500">
                                    <span className="truncate max-w-[70px]">vs {match.opponent}</span>
                                    <span>{match.score}</span>
                                </div>
                            </div>
                        ))}
                        {(!p2Form || p2Form.length === 0) && (
                            <span className="text-[9px] text-slate-600 font-bold block">No recent matches</span>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────
//  Alt bileşen: Player History Drawer
// ─────────────────────────────────────────────────────────────
function PlayerHistoryDrawer({ playerId, playerName, onClose }) {
    const [matches, setMatches] = useState([]);
    const [loading, setLoading] = useState(true);
    const [totalMatches, setTotalMatches] = useState(0);

    useEffect(() => {
        if (!playerId) return;
        setLoading(true);
        apiClient.get(`/tennis/player-history/${playerId}?limit=15`)
            .then(res => {
                setMatches(res.data?.matches || []);
                setTotalMatches(res.data?.total_matches || 0);
            })
            .catch(() => setMatches([]))
            .finally(() => setLoading(false));
    }, [playerId]);

    if (!playerId) return null;

    return (
        <div className="fixed inset-0 z-[100] flex justify-end" onClick={onClose}>
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
            {/* Drawer */}
            <div
                className="relative w-full max-w-md bg-slate-950 border-l border-slate-800 h-full overflow-y-auto animate-slide-in-right"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="sticky top-0 z-10 bg-slate-950/95 backdrop-blur-xl border-b border-slate-900 p-4 flex items-center justify-between">
                    <div>
                        <h3 className="text-sm font-black text-white uppercase tracking-wider">{playerName}</h3>
                        <span className="text-[9px] text-slate-500 font-bold">{totalMatches} Career Matches Tracked</span>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-slate-800 cursor-pointer"
                    >
                        ✕
                    </button>
                </div>
                {/* Content */}
                <div className="p-4 space-y-2">
                    {loading ? (
                        <div className="space-y-3 animate-pulse">
                            {[1, 2, 3, 4, 5].map(i => <div key={i} className="h-14 bg-slate-900/50 rounded-xl" />)}
                        </div>
                    ) : matches.length === 0 ? (
                        <div className="text-center py-10">
                            <span className="text-2xl">📭</span>
                            <p className="text-xs text-slate-500 font-bold mt-2">No match history found</p>
                        </div>
                    ) : (
                        matches.map((m, i) => {
                            const isHome = m.home_player?.toLowerCase().includes(playerName?.split(' ')[0]?.toLowerCase() || '');
                            const won = (m.winner === 'home' && isHome) || (m.winner === 'away' && !isHome);
                            const opponent = isHome ? m.away_player : m.home_player;
                            const hScore = m.home_score ?? 0;
                            const aScore = m.away_score ?? 0;
                            const score = isHome ? `${hScore}-${aScore}` : `${aScore}-${hScore}`;
                            const surface = (m.ground || 'Unknown').toLowerCase();
                            const surfaceColor = surface.includes('clay') ? 'text-amber-400 bg-amber-950/40 border-amber-500/25'
                                : surface.includes('grass') ? 'text-emerald-400 bg-emerald-950/40 border-emerald-500/25'
                                    : 'text-blue-400 bg-blue-950/40 border-blue-500/25';

                            return (
                                <div key={i} className="flex items-center gap-3 bg-slate-900/30 border border-slate-900/60 rounded-xl p-3 hover:border-slate-800 transition-all">
                                    <span className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-black border
                                        ${won ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30' : 'bg-rose-950/60 text-rose-400 border-rose-500/30'}`}>
                                        {won ? 'W' : 'L'}
                                    </span>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-1.5">
                                            <span className="text-[10px] font-black text-white truncate">{opponent}</span>
                                            <span className="text-[9px] font-black text-slate-400">{score}</span>
                                        </div>
                                        <div className="flex items-center gap-1.5 mt-0.5">
                                            <span className={`text-[7px] font-black uppercase px-1.5 py-0.5 rounded border ${surfaceColor}`}>{m.ground}</span>
                                            <span className="text-[8px] text-slate-500 font-bold truncate">{(m.tournament || '').split('(')[0].trim()}</span>
                                        </div>
                                    </div>
                                    <span className="text-[9px] text-slate-600 font-bold flex-shrink-0">{m.date}</span>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────
//  Alt bileşen: Tekil Maç Kartı
// ─────────────────────────────────────────────────────────────
function MatchCard({ predict, isResultCard, onPlayerClick }) {
    const [expanded, setExpanded] = useState(false);
    const [statsExpanded, setStatsExpanded] = useState(false);

    const surface = getSurfaceStyles(predict.surface);
    const hasOdds = predict.p1_odds != null && predict.p2_odds != null;
    const hasEdge = predict.edge_percentage != null && predict.edge_percentage > 0;
    const hasKelly = predict.recommended_kelly_bet_percentage != null && predict.recommended_kelly_bet_percentage > 0;
    const showMetrics = hasOdds || hasEdge || hasKelly;

    const p1American = formatOdds(predict.p1_odds);
    const p2American = formatOdds(predict.p2_odds);

    const highConfAlt = predict.alternative_bets?.filter(a => a.confidence === 'High') || [];
    const hasHighConf = highConfAlt.length > 0;

    // Results tabındaki veriler için: predicted_winner rakam olabilir (1 ya da 2)
    const winnerPlayer =
        typeof predict.predicted_winner === 'number'
            ? predict.predicted_winner === 1 ? predict.home_player : predict.away_player
            : predict.predicted_winner;

    const isWta = (predict.tournament || '').toUpperCase().includes('WTA') || (predict.tournament || '').toUpperCase().includes('CHALLENGER WOMEN');
    const rankLabel = isWta ? 'WTA RANK' : 'ATP RANK';

    return (
        <div
            className={`relative rounded-3xl p-5 flex flex-col gap-4 transition-all duration-300 shadow-lg group overflow-hidden
                ${hasHighConf
                    ? 'bg-slate-900/35 border border-indigo-500/30 hover:border-indigo-400/50 shadow-[0_0_20px_rgba(99,102,241,0.07)]'
                    : 'bg-slate-900/30 border border-slate-850 hover:border-slate-800'
                }`}
        >
            {/* Arkaplan parlama — sadece High conf varsa */}
            {hasHighConf && (
                <div className="absolute inset-0 pointer-events-none rounded-3xl bg-gradient-to-br from-indigo-500/[0.04] to-transparent" />
            )}

            {/* ── Üst: Turnuva + Zemin + Saat/Tur + Match ID ── */}
            <div className="flex justify-between items-start border-b border-slate-950/60 pb-3 gap-2 relative z-10">
                <div className="flex flex-col min-w-0">
                    <span className="text-[10px] text-slate-300 font-black uppercase tracking-wider block truncate max-w-[200px] sm:max-w-[300px]">
                        {predict.tournament}
                    </span>
                    <div className="flex items-center gap-1.5 flex-wrap mt-1.5">
                        <span className={`inline-flex items-center gap-1.5 text-[8px] font-black uppercase border px-2 py-0.5 rounded-full ${surface.bg}`}>
                            <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${surface.dot}`} />
                            {surface.label} Court
                        </span>
                        {predict.match_stage && (
                            <span className="text-[8px] text-indigo-400 bg-indigo-950/50 border border-indigo-500/20 px-2 py-0.5 rounded-full font-black uppercase tracking-wider">
                                {predict.match_stage}
                            </span>
                        )}
                        {predict.match_time && predict.match_time !== 'TBD' && (
                            <span className="text-[8px] text-cyan-400 bg-cyan-950/50 border border-cyan-500/20 px-2 py-0.5 rounded-full font-black uppercase tracking-wider">
                                🕒 {predict.match_time}
                            </span>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                    {predict.isLowConfidence && !isResultCard && (
                        <div
                            className="text-[8px] font-black uppercase tracking-widest px-2.5 py-0.5 rounded-lg border bg-amber-600/30 border-amber-500/50 text-amber-300 flex items-center gap-1"
                            title="Low confidence prediction — use caution"
                            role="img"
                            aria-label="Low confidence prediction — use caution"
                        >
                            <span>⚠️</span>
                            <span>Risky</span>
                        </div>
                    )}
                    {isResultCard && (
                        <span className={`text-[8px] font-black uppercase tracking-widest px-2 py-0.5 rounded border ${predict.is_correct ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30' : 'bg-rose-950/60 text-rose-400 border-rose-500/30'}`}>
                            {predict.is_correct ? '✓ Correct' : '✗ Wrong'}
                        </span>
                    )}
                    <span className="text-[8px] text-slate-500 font-extrabold uppercase tracking-widest bg-slate-950/50 border border-slate-850 px-2 py-1 rounded">
                        #{predict.match_id?.slice(-4)}
                    </span>
                </div>
            </div>

            {/* ── Oyuncular + Olasılık Barı ── */}
            <div className="space-y-3 relative z-10">
                {/* P1 */}
                <div className="flex justify-between items-center gap-2">
                    <div className="flex items-center gap-3 min-w-0">
                        {/* Circular initials avatar */}
                        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 flex items-center justify-center text-[9px] font-black text-slate-400 group-hover:border-indigo-500/30 transition-all select-none shadow-[0_0_8px_rgba(0,0,0,0.5)]">
                            {getPlayerInitials(predict.home_player)}
                        </div>

                        <div className="space-y-0.5 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                                <button
                                    onClick={(e) => { e.stopPropagation(); onPlayerClick?.(predict.p1_id, predict.home_player); }}
                                    className={`text-xs font-black block truncate max-w-[130px] sm:max-w-[180px] leading-tight cursor-pointer hover:underline decoration-dotted underline-offset-2 transition-all text-left
                                        ${winnerPlayer === predict.home_player ? 'text-indigo-400 hover:text-indigo-300' : 'text-gray-300 hover:text-white'}`}
                                >
                                    {predict.home_player}
                                    {winnerPlayer === predict.home_player && ' 🎯'}
                                </button>
                                {hasOdds && p1American && (
                                    <span className="text-[9px] font-bold text-slate-500 bg-slate-950/60 border border-slate-900/80 px-1.5 py-0.5 rounded flex-shrink-0">
                                        {p1American} <span className="text-[8px] text-slate-600">({predict.p1_odds})</span>
                                    </span>
                                )}
                            </div>

                            <div className="flex items-center gap-1.5 flex-wrap text-slate-600">
                                {predict.p1_stats?.rank && (
                                    <span className="text-[8px] text-slate-500 font-black">{rankLabel} #{predict.p1_stats.rank}</span>
                                )}
                            </div>
                        </div>
                    </div>
                    <span className="text-xs font-black text-gray-300 flex-shrink-0">{predict.home_win_probability}%</span>
                </div>

                {/* Progress Bar */}
                <div className="w-full bg-slate-950/80 rounded-full h-2 border border-slate-900/60 overflow-hidden flex shadow-inner">
                    <div
                        className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 rounded-l-full shadow-[0_0_8px_rgba(99,102,241,0.4)] transition-all duration-700"
                        style={{ width: `${predict.home_win_probability}%` }}
                    />
                    <div
                        className="h-full bg-slate-800 rounded-r-full"
                        style={{ width: `${predict.away_win_probability}%` }}
                    />
                </div>

                {/* P2 */}
                <div className="flex justify-between items-center gap-2">
                    <div className="flex items-center gap-3 min-w-0">
                        {/* Circular initials avatar */}
                        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 flex items-center justify-center text-[9px] font-black text-slate-400 group-hover:border-indigo-500/30 transition-all select-none shadow-[0_0_8px_rgba(0,0,0,0.5)]">
                            {getPlayerInitials(predict.away_player)}
                        </div>

                        <div className="space-y-0.5 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                                <button
                                    onClick={(e) => { e.stopPropagation(); onPlayerClick?.(predict.p2_id, predict.away_player); }}
                                    className={`text-xs font-black block truncate max-w-[130px] sm:max-w-[180px] leading-tight cursor-pointer hover:underline decoration-dotted underline-offset-2 transition-all text-left
                                        ${winnerPlayer === predict.away_player ? 'text-indigo-400 hover:text-indigo-300' : 'text-gray-300 hover:text-white'}`}
                                >
                                    {predict.away_player}
                                    {winnerPlayer === predict.away_player && ' 🎯'}
                                </button>
                                {hasOdds && p2American && (
                                    <span className="text-[9px] font-bold text-slate-500 bg-slate-950/60 border border-slate-900/80 px-1.5 py-0.5 rounded flex-shrink-0">
                                        {p2American} <span className="text-[8px] text-slate-600">({predict.p2_odds})</span>
                                    </span>
                                )}
                            </div>

                            <div className="flex items-center gap-1.5 flex-wrap text-slate-600">
                                {predict.p2_stats?.rank && (
                                    <span className="text-[8px] text-slate-500 font-black">{rankLabel} #{predict.p2_stats.rank}</span>
                                )}
                            </div>
                        </div>
                    </div>
                    <span className="text-xs font-black text-gray-300 flex-shrink-0">{predict.away_win_probability}%</span>
                </div>
            </div>

            {/* Scoreboard (Set Skorları) */}
            {predict.set_scores && predict.set_scores.length > 0 && (
                <div className="flex items-center gap-1.5 bg-slate-950/50 border border-slate-900 px-3 py-1.5 rounded-2xl w-max self-center relative z-10 shadow-inner">
                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider mr-1">Scoreboard</span>
                    {predict.set_scores.map((set, idx) => (
                        <div key={idx} className="flex items-center gap-1 text-[10px] font-black bg-slate-900 border border-slate-850 px-2 py-0.5 rounded-lg select-none">
                            <span className="text-indigo-400">{set.home}</span>
                            <span className="text-slate-600">:</span>
                            <span className="text-indigo-400">{set.away}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* ── Edge & Kelly (Sadece gerçek veri varsa göster) ── */}
            {showMetrics && (
                <div className="grid grid-cols-2 gap-3 bg-slate-950/60 border border-slate-900 rounded-2xl p-3.5 shadow-inner relative z-10">
                    {/* Edge */}
                    <div className="border-r border-slate-900 space-y-0.5 pr-3">
                        <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Mathematical Edge</span>
                        {hasEdge ? (
                            <span className="text-xs font-black text-emerald-400 flex items-center gap-1">
                                📈 +{predict.edge_percentage}%
                            </span>
                        ) : (
                            <span className="text-xs font-black text-slate-600">—</span>
                        )}
                    </div>
                    {/* Kelly */}
                    <div className="space-y-0.5 pl-1">
                        <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Kelly Staking</span>
                        {hasKelly ? (
                            <span className="text-xs font-black text-indigo-400">
                                💼 {predict.recommended_kelly_bet_percentage}%
                            </span>
                        ) : (
                            <span className="text-xs font-black text-slate-600">—</span>
                        )}
                    </div>
                </div>
            )}
            {/* ── Röntgen & AI Insights Accordion ── */}
            {((predict.alternative_bets && predict.alternative_bets.length > 0) || (predict.p1_stats && predict.p2_stats) || predict.ai_insight || (predict.h2h_summary && predict.h2h_summary.total_matches > 0)) && (
                <div className="border-t border-slate-900/70 pt-3 relative z-10">
                    <button
                        onClick={() => setExpanded(p => !p)}
                        className="w-full flex items-center justify-between cursor-pointer focus:outline-none group/acc"
                    >
                        <span className="flex items-center gap-1.5 text-[9px] font-black uppercase tracking-widest text-slate-400 group-hover/acc:text-indigo-300 transition-colors flex-wrap">
                            <span className={`transition-all ${hasHighConf ? 'text-indigo-400' : ''}`}>⚡</span>
                            Röntgen &amp; AI Edge
                            {predict.alternative_bets && predict.alternative_bets.length > 0 && (
                                <span className={`px-1.5 py-0.5 rounded text-[8px] font-black border ${hasHighConf ? 'bg-indigo-950/60 text-indigo-400 border-indigo-500/30' : 'bg-slate-900 text-slate-500 border-slate-800'}`}>
                                    {predict.alternative_bets.length} Plays
                                </span>
                            )}
                            {predict.ai_insight && (
                                <span className="text-[8px] font-black text-cyan-400 bg-cyan-950/50 border border-cyan-500/20 px-1.5 py-0.5 rounded uppercase">
                                    💡 Insight
                                </span>
                            )}
                            {hasHighConf && (
                                <span className="text-[8px] font-black text-emerald-400 bg-emerald-950/50 border border-emerald-500/20 px-1.5 py-0.5 rounded animate-pulse">
                                    {highConfAlt.length} HIGH
                                </span>
                            )}
                        </span>
                        <span className="text-[9px] text-slate-500 group-hover/acc:text-slate-300 transition-colors font-bold">
                            {expanded ? '▲' : '▼'}
                        </span>
                    </button>

                    {expanded && (
                        <div className="mt-3 space-y-4">
                            {/* 1. AI Edge Insight Narrative */}
                            {predict.ai_insight && (
                                <div className="space-y-1.5">
                                    <span className="text-[7.5px] font-black uppercase tracking-widest text-slate-500 block">🧠 AI Edge Insight</span>
                                    {renderAiInsight(predict.ai_insight)}
                                </div>
                            )}

                            {/* 2. H2H Head-to-Head History */}
                            {predict.h2h_summary && predict.h2h_summary.total_matches > 0 && (
                                <div className="space-y-1.5">
                                    <H2HSummary h2h={predict.h2h_summary} p1Name={predict.home_player} p2Name={predict.away_player} />
                                </div>
                            )}

                            {/* Recent Form History (Last 5 Matches) */}
                            <RecentFormHistory
                                p1Name={predict.home_player}
                                p1Form={predict.p1_stats?.recent_form}
                                p2Name={predict.away_player}
                                p2Form={predict.p2_stats?.recent_form}
                            />

                            {/* 3. Röntgen Matchup Stats Comparison */}
                            {predict.p1_stats && predict.p2_stats && (
                                <div className="space-y-2">
                                    <button
                                        onClick={() => setStatsExpanded(p => !p)}
                                        className="w-full flex items-center justify-between bg-slate-950/60 border border-slate-900/80 hover:border-slate-800 rounded-xl px-3.5 py-2.5 cursor-pointer text-[9px] font-black uppercase tracking-wider text-slate-400 hover:text-white transition-all duration-200"
                                    >
                                        <span className="flex items-center gap-2">
                                            <span>📊</span> Röntgen Sabermetrics Matchup
                                        </span>
                                        <span className="text-[8px] font-bold text-slate-500">
                                            {statsExpanded ? '▲ CLOSE' : '▼ OPEN MATCHUP'}
                                        </span>
                                    </button>
                                    {statsExpanded && (
                                        <StatsComparison p1={predict.p1_stats} p2={predict.p2_stats} />
                                    )}
                                </div>
                            )}

                            {/* 4. Alternative Bahis Önerileri */}
                            {predict.alternative_bets && predict.alternative_bets.length > 0 && (
                                <div className="space-y-2.5">
                                    <span className="text-[7.5px] font-black uppercase tracking-widest text-slate-500 block">🎯 Alternative Plays</span>
                                    <div className="space-y-2">
                                        {predict.alternative_bets.map((alt, idx) => {
                                            const isHigh = alt.confidence === 'High';
                                            return (
                                                <div
                                                    key={idx}
                                                    className={`rounded-xl p-3.5 space-y-2 transition-all
                                                        ${isHigh
                                                            ? 'bg-indigo-950/20 border border-indigo-500/25 shadow-[0_0_18px_rgba(99,102,241,0.12)]'
                                                            : 'bg-slate-950/40 border border-slate-900/60'
                                                        }`}
                                                >
                                                    <div className="flex justify-between items-center gap-2">
                                                        <div className="flex items-center gap-2 min-w-0 flex-wrap">
                                                            <span className={`text-[8px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded border flex-shrink-0
                                                                ${isHigh
                                                                    ? 'bg-indigo-950/80 text-indigo-300 border-indigo-500/30'
                                                                    : 'bg-slate-900 text-slate-500 border-slate-850'
                                                                }`}>
                                                                {alt.market}
                                                            </span>
                                                            <strong className={`text-[11px] font-black leading-tight ${isHigh ? 'text-white' : 'text-indigo-300'}`}>
                                                                {alt.selection}
                                                            </strong>
                                                        </div>
                                                        <span className={`text-[7px] font-black tracking-wider uppercase px-2 py-0.5 rounded-full border flex-shrink-0
                                                            ${isHigh
                                                                ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30 shadow-[0_0_8px_rgba(52,211,153,0.2)]'
                                                                : 'bg-amber-950/40 text-amber-400 border-amber-500/20'
                                                            }`}>
                                                            {isHigh ? '🔥 HIGH' : 'MED'}
                                                        </span>
                                                    </div>

                                                    <p className={`text-[10px] leading-relaxed font-medium ${isHigh ? 'text-slate-300' : 'text-slate-400'}`}>
                                                        {isHigh ? '💡 ' : ''}
                                                        {alt.reason}
                                                    </p>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}        </div>
    );
}

// ─────────────────────────────────────────────────────────────
//  Alt bileşen: Maç Listesi Grid
// ─────────────────────────────────────────────────────────────
function MatchGrid({ list, isResultCard, emptyMessage, onPlayerClick }) {
    if (!list || list.length === 0) {
        return (
            <div className="bg-slate-900/20 border border-slate-850 rounded-3xl p-10 text-center max-w-md mx-auto my-6 animate-fade-in select-none">
                <span className="text-3xl block mb-2">📭</span>
                <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest">No Matches Found</h4>
                <p className="text-[10px] text-slate-500 font-semibold mt-1">{emptyMessage}</p>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {list.map(predict => (
                <MatchCard
                    key={predict.match_id}
                    predict={predict}
                    isResultCard={isResultCard}
                    onPlayerClick={onPlayerClick}
                />
            ))}
        </div>
    );
}

// ─────────────────────────────────────────────────────────────
//  ANA BİLEŞEN
// ─────────────────────────────────────────────────────────────
function TennisDashboard({ selectedDate }) {
    const { data, loading, error, isPreparing } = useTennisPredictions(selectedDate);

    // GÖREV 1: Upcoming vs Results ana tab
    const [matchView, setMatchView] = useState('upcoming');  // 'upcoming' | 'results'

    // GÖREV 8: Tour & Tournament Filtreleri
    const [tourFilter, setTourFilter] = useState('ALL'); // 'ALL' | 'ATP' | 'WTA' | 'CHALLENGER'
    const [selectedTourney, setSelectedTourney] = useState('ALL'); // 'ALL' | string

    // Player History Drawer state
    const [drawerPlayer, setDrawerPlayer] = useState(null); // { id, name }
    const handlePlayerClick = useCallback((playerId, playerName) => {
        if (playerId) setDrawerPlayer({ id: playerId, name: playerName });
    }, []);
    const closeDrawer = useCallback(() => setDrawerPlayer(null), []);

    // ── Error ──
    if (error && !data) {
        return (
            <div className="bg-rose-950/30 border border-rose-500/30 rounded-3xl p-6 md:p-8 text-center max-w-xl mx-auto my-10 animate-fade-in">
                <span className="text-4xl block mb-3">⚠️</span>
                <h3 className="text-base font-black text-rose-400 uppercase tracking-widest mb-2">API Connection Error</h3>
                <p className="text-xs text-slate-300 leading-relaxed font-semibold">{error}</p>
            </div>
        );
    }

    // ── Cold start ──
    if (isPreparing) {
        return (
            <div className="bg-slate-900/60 backdrop-blur-xl border border-indigo-500/30 rounded-3xl p-8 text-center max-w-md mx-auto my-10 shadow-[0_0_50px_rgba(99,102,241,0.15)] flex flex-col items-center">
                <div className="relative mb-6">
                    <span className="text-6xl inline-block animate-spin [animation-duration:3s]">🎾</span>
                    <div className="absolute inset-0 rounded-full bg-indigo-500/10 blur-xl animate-pulse" />
                </div>
                <h2 className="text-lg font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-indigo-400 uppercase tracking-widest mb-3">
                    Waking Up Tennis AI Engine
                </h2>
                <p className="text-slate-300 text-xs font-semibold leading-relaxed mb-6">
                    The backend container is waking up. Predictions and ELO calculations will load in about 30 seconds.
                </p>
                <div className="w-full bg-slate-950/85 rounded-full h-1.5 p-[1px] border border-slate-800 mb-5 relative overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 rounded-full w-2/3 animate-pulse shadow-[0_0_10px_rgba(99,102,241,0.5)]" />
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-full">
                    <span className="flex h-1.5 w-1.5 relative">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-cyan-500" />
                    </span>
                    <span className="text-[10px] text-indigo-300 font-extrabold uppercase tracking-widest animate-pulse">Auto-refreshing...</span>
                </div>
            </div>
        );
    }

    // ── Loading Skeletons ──
    if (loading && !data) {
        return (
            <div className="space-y-8 animate-pulse">
                <div className="h-28 bg-slate-900/40 border border-slate-850 rounded-3xl" />
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map(i => <div key={i} className="h-20 bg-slate-900/30 border border-slate-850 rounded-2xl" />)}
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                    {[1, 2, 3, 4].map(i => <div key={i} className="h-64 bg-slate-900/30 border border-slate-850 rounded-3xl" />)}
                </div>
            </div>
        );
    }

    // ── Veri çözümleme ──
    const predictions = data?.predictions || {};
    const results = data?.results || null;
    const lastUpdated = data?.last_updated || 'Unknown';

    const activePredictions = predictions.active_predictions || [];
    const skippedLowConfidence = predictions.skipped_low_confidence || [];
    const skippedLowTier = predictions.skipped_low_tier || [];
    const stats = predictions.statistics || {};

    // Results tab için veri
    const activeResults = results?.active_results || [];
    const lowConfResults = results?.low_confidence_results || [];
    const altLeagueResults = results?.alt_league_results || [];

    // Merge all predictions into single list (no category tabs anymore)
    const allUpcomingMatches = [
        ...activePredictions,
        ...skippedLowTier,
        ...skippedLowConfidence
    ];

    // Merge all results
    const allResultsMatches = [
        ...activeResults,
        ...altLeagueResults,
        ...lowConfResults
    ];

    const hasResults = results && results.active_statistics && results.active_statistics.total_predicted > 0;

    const currentCategoryList = matchView === 'upcoming' ? allUpcomingMatches : allResultsMatches;

    // 1. Tour Filter (ATP / WTA / CHALLENGER / ALL) - ISOLATED
    const tourFilteredList = currentCategoryList.filter(predict => {
        const tName = (predict.tournament || '').toUpperCase();
        if (tourFilter === 'ALL') return true;
        if (tourFilter === 'ATP') return tName.includes('ATP') && !tName.includes('CHALLENGER');
        if (tourFilter === 'WTA') return tName.includes('WTA') && !tName.includes('CHALLENGER');
        if (tourFilter === 'CHALLENGER') return tName.includes('CHALLENGER');
        return true;
    });

    // 2. Unique tournaments (based on current tour filter)
    const uniqueTourneys = Array.from(new Set(tourFilteredList.map(p => p.tournament))).filter(Boolean).sort();

    // 3. Tournament Filter (fallback to ALL if previous selection is invalid in current tour context)
    const isSelectedTourneyValid = uniqueTourneys.includes(selectedTourney);
    const activeSelectedTourney = isSelectedTourneyValid ? selectedTourney : 'ALL';

    const finalMatchList = tourFilteredList.filter(predict => {
        if (activeSelectedTourney === 'ALL') return true;
        return predict.tournament === activeSelectedTourney;
    });

    return (
        <div className="space-y-7 animate-fade-in pb-12 selection:bg-indigo-500 selection:text-white">

            {/* ── BAŞLIK BANNERI ── */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/40 border border-slate-850 p-5 sm:p-6 rounded-3xl backdrop-blur-xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-48 h-48 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />
                <div className="space-y-1.5 relative z-10 text-center md:text-left">
                    <div className="flex items-center justify-center md:justify-start gap-2.5 flex-wrap">
                        <span className="text-2xl sm:text-3xl">🎾</span>
                        <h2 className="text-lg sm:text-xl md:text-2xl font-black text-white uppercase tracking-wider">
                            Tennis Match Projections
                        </h2>
                        <span className="text-[9px] font-black tracking-widest text-cyan-400 bg-cyan-950/50 border border-cyan-500/30 px-2 py-0.5 rounded-md uppercase">
                            BETA
                        </span>
                    </div>
                    <p className="text-xs text-slate-400 font-semibold max-w-2xl leading-relaxed mx-auto md:mx-0">
                        Markov chain-based point simulator — calculates tennis matchups point-by-point to generate game totals, set spreads, and moneyline edges.
                    </p>
                </div>
                <div className="flex flex-col items-center md:items-end justify-center self-center md:self-auto text-center md:text-right relative z-10">
                    <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">LAST UPDATED (ET)</span>
                    <span className="text-xs text-slate-300 font-extrabold mt-0.5 bg-slate-950/40 border border-slate-850 px-3 py-1 rounded-lg">
                        ⏱️ {lastUpdated.split(' ')[1] || lastUpdated}
                    </span>
                </div>
            </div>

            {/* ── ACCURACY CARD (yalnızca biten maç varsa) ── */}
            {hasResults && (
                <div className="bg-emerald-950/15 border border-emerald-500/20 rounded-3xl p-5 md:p-6 shadow-[0_10px_35px_rgba(16,185,129,0.05)] relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none" />
                    <div className="flex flex-col md:flex-row items-center justify-between gap-5 relative z-10">
                        <div className="space-y-1 text-center md:text-left">
                            <span className="text-[9px] text-emerald-400 font-black uppercase tracking-widest bg-emerald-950/60 border border-emerald-500/25 px-2.5 py-0.5 rounded-full">
                                ✓ Live Accuracy Verification
                            </span>
                            <h4 className="text-sm md:text-base font-black text-white tracking-wider uppercase mt-1">Today's Model Performance</h4>
                            <p className="text-xs text-slate-400 font-medium leading-relaxed max-w-xl">
                                Real-time accuracy tracked across all finished matches.
                            </p>
                        </div>
                        <div className="grid grid-cols-3 gap-3 w-full md:w-auto text-center">
                            {[
                                { label: 'Main Plays', stat: results.active_statistics, color: 'text-emerald-400' },
                                { label: 'Risky Picks', stat: results.low_confidence_statistics, color: 'text-amber-400' },
                                { label: 'Alt Leagues', stat: results.alt_league_statistics, color: 'text-cyan-400' },
                            ].map(({ label, stat, color }) => (
                                <div key={label} className="bg-slate-950/50 border border-slate-900 rounded-2xl p-3 min-w-[90px]">
                                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">{label}</span>
                                    <span className={`text-base font-black block mt-0.5 ${color}`}>{stat?.accuracy_percentage ?? 0}%</span>
                                    <span className="text-[8px] text-slate-500 font-bold block mt-0.5">
                                        {stat?.correct_predictions ?? 0}/{stat?.total_predicted ?? 0} W
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* ── TOURNAMENT & TOUR FILTERS ── */}
            <div className="bg-slate-900/35 border border-slate-850/60 rounded-3xl p-5 shadow-inner">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1.5">
                        <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Tour Filter</span>
                        <div className="flex items-center gap-1.5 flex-wrap">
                            {[
                                { id: 'ALL', label: 'All Tours', badgeColor: 'bg-indigo-600/20 border-indigo-500/30 text-indigo-400' },
                                { id: 'ATP', label: 'ATP Tour', badgeColor: 'bg-blue-600/20 border-blue-500/30 text-blue-400' },
                                { id: 'WTA', label: 'WTA Tour', badgeColor: 'bg-purple-600/20 border-purple-500/30 text-purple-400' },
                                { id: 'CHALLENGER', label: 'Challenger Tour', badgeColor: 'bg-amber-600/20 border-amber-500/30 text-amber-400' }
                            ].map(tour => {
                                const isActive = tourFilter === tour.id;
                                return (
                                    <button
                                        key={tour.id}
                                        onClick={() => {
                                            setTourFilter(tour.id);
                                            setSelectedTourney('ALL');
                                        }}
                                        className={`px-3 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-widest border transition-all cursor-pointer select-none
                                            ${isActive ? tour.badgeColor : 'bg-slate-950/60 border-slate-900/80 text-slate-400 hover:text-slate-200'}`}
                                    >
                                        {tour.label}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    <div className="space-y-1.5 flex-1 max-w-xs">
                        <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Tournament Selector</span>
                        <select
                            value={activeSelectedTourney}
                            onChange={(e) => setSelectedTourney(e.target.value)}
                            className="w-full bg-slate-950/80 border border-slate-900 hover:border-slate-800 focus:border-indigo-500/50 text-[10px] font-black uppercase tracking-wider text-slate-300 rounded-xl px-3 py-2 cursor-pointer focus:outline-none"
                        >
                            <option value="ALL" className="bg-slate-950 text-slate-300">All Tournaments ({tourFilteredList.length} Match{tourFilteredList.length !== 1 ? 'es' : ''})</option>
                            {uniqueTourneys.map(t => (
                                <option key={t} value={t} className="bg-slate-950 text-slate-300">{t}</option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* ── TOUR FILTER EXPANSION: Add Challenger Tour Button ── */}

            {/* ── GÖREV 1: UPCOMING / RESULTS ANA SEKMELERİ ── */}
            <div className="flex items-center gap-1 p-1 bg-slate-950/70 border border-slate-900 rounded-2xl w-full sm:w-max shadow-inner">
                <button
                    id="tab-upcoming"
                    onClick={() => setMatchView('upcoming')}
                    className={`flex-1 sm:flex-none px-5 py-2 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all duration-200 cursor-pointer flex items-center justify-center gap-2
                        ${matchView === 'upcoming'
                            ? 'bg-gradient-to-br from-indigo-600/90 to-blue-700/90 text-white shadow-[0_0_15px_rgba(99,102,241,0.35)] border border-indigo-400/30'
                            : 'text-slate-400 hover:text-slate-200 border border-transparent hover:bg-slate-900/60'
                        }`}
                >
                    🕐 Upcoming
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-black border
                        ${matchView === 'upcoming' ? 'bg-indigo-950/60 border-indigo-400/30 text-indigo-200' : 'bg-slate-900 border-slate-800 text-slate-500'}`}>
                        {activePredictions.length + skippedLowTier.length + skippedLowConfidence.length}
                    </span>
                </button>
                <button
                    id="tab-results"
                    onClick={() => setMatchView('results')}
                    className={`flex-1 sm:flex-none px-5 py-2 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all duration-200 cursor-pointer flex items-center justify-center gap-2
                        ${matchView === 'results'
                            ? 'bg-gradient-to-br from-emerald-600/80 to-teal-700/80 text-white shadow-[0_0_15px_rgba(16,185,129,0.3)] border border-emerald-400/30'
                            : 'text-slate-400 hover:text-slate-200 border border-transparent hover:bg-slate-900/60'
                        }`}
                >
                    ✓ Results
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-black border
                        ${matchView === 'results' ? 'bg-emerald-950/60 border-emerald-400/30 text-emerald-200' : 'bg-slate-900 border-slate-800 text-slate-500'}`}>
                        {activeResults.length + lowConfResults.length + altLeagueResults.length}
                    </span>
                </button>
            </div>

            {/* ── MAÇ LİSTESİ (TÜM RISK SEVİYELERİ) ── */}
            {matchView === 'upcoming' ? (
                <MatchGrid
                    list={finalMatchList.map(m => ({ ...m, isLowConfidence: skippedLowConfidence.some(rc => rc.match_id === m.match_id) }))}
                    isResultCard={false}
                    emptyMessage="No upcoming tennis matches calculated for these filters."
                    onPlayerClick={handlePlayerClick}
                />
            ) : (
                <MatchGrid
                    list={finalMatchList.map(m => ({ ...m, isLowConfidence: lowConfResults.some(rc => rc.match_id === m.match_id) }))}
                    isResultCard={true}
                    emptyMessage="No finished matches available yet for these filters."
                    onPlayerClick={handlePlayerClick}
                />
            )}

            {/* ── PLAYER HISTORY DRAWER ── */}
            {drawerPlayer && (
                <PlayerHistoryDrawer
                    playerId={drawerPlayer.id}
                    playerName={drawerPlayer.name}
                    onClose={closeDrawer}
                />
            )}

            {/* ── ÖZET İSTATİSTİK KARTI (SAYFA ALTINA TAŞINDI) ── */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-slate-900/35 border border-slate-850 rounded-2xl p-4 flex flex-col justify-between">
                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider">Main Plays</span>
                    <span className="text-xl font-black text-white mt-1">{activePredictions.length}</span>
                </div>
                <div className="bg-slate-900/35 border border-slate-850 rounded-2xl p-4 flex flex-col justify-between">
                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider">Challenger Tour</span>
                    <span className="text-xl font-black text-cyan-400 mt-1">{skippedLowTier.length}</span>
                </div>
                <div className="bg-slate-900/35 border border-slate-850 rounded-2xl p-4 flex flex-col justify-between">
                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider">Risky Picks</span>
                    <span className="text-xl font-black text-amber-500 mt-1">{skippedLowConfidence.length}</span>
                </div>
                <div className="bg-slate-900/35 border border-slate-850 rounded-2xl p-4 flex flex-col justify-between">
                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider">Results In</span>
                    <span className="text-xl font-black text-slate-300 mt-1">{activeResults.length}</span>
                </div>
            </div>

            {/* ── METODOLOJİ PANELİ ── */}
            <div className="bg-slate-900/40 border border-slate-850 rounded-3xl p-5">
                <h4 className="text-xs font-black text-white uppercase tracking-wider mb-2">Tennis Point Simulation Methodology</h4>
                <p className="text-xs text-slate-400 leading-relaxed font-semibold">
                    Calculations use a point-by-point Markov simulator. By resolving each player's serve hold rates and opponent return success across the current court surface (Hard, Clay, or Grass), the simulator models set coverages and game totals over 10,000 iterations to isolate betting margins (edges) against market lines.
                </p>
            </div>
        </div>
    );
}

export default TennisDashboard;
