import React, { useState } from 'react';
import { useWnbaPredictions } from '../hooks/useWnbaPredictions';

// ─────────────────────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────────────────────

function displayAmericanOdds(val) {
    if (val === undefined || val === null || val === '') return '—';
    const n = parseInt(val, 10);
    if (Number.isNaN(n)) return '—';
    return n > 0 ? `+${n}` : `${n}`;
}

function formatSignedValue(val) {
    if (val === undefined || val === null) return '—';
    const num = parseFloat(val);
    if (Number.isNaN(num)) return '—';
    return num > 0 ? `+${num.toFixed(1)}` : num.toFixed(1);
}

function formatPct(val) {
    if (val === undefined || val === null) return '—';
    const n = parseFloat(val);
    if (Number.isNaN(n)) return '—';
    return `${(n * 100).toFixed(1)}%`;
}

function renderAiInsight(text) {
    if (!text) return null;

    const bullets = text.split('\n')
        .map(l => l.trim())
        .filter(l => l.startsWith('-') || l.startsWith('*'));

    if (bullets.length === 3) {
        const titles = ['Team Strength', 'Situational Factors', 'Betting Angle'];
        const icons = ['💪', '🔋', '🎯'];
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

function TeamLogo({ logo, abbr, size = 'md' }) {
    const dim = size === 'lg' ? 'w-9 h-9' : 'w-8 h-8';
    return (
        <div className={`flex-shrink-0 ${dim} rounded-full bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 flex items-center justify-center overflow-hidden shadow-[0_0_8px_rgba(0,0,0,0.5)] group-hover:border-indigo-500/30 transition-all`}>
            {logo ? (
                <img
                    src={logo}
                    alt={abbr || 'team'}
                    className="w-full h-full object-contain p-0.5"
                    onError={(e) => {
                        e.target.style.display = 'none';
                        if (e.target.nextSibling) e.target.nextSibling.style.display = 'flex';
                    }}
                />
            ) : null}
            <span
                className={`w-full h-full items-center justify-center text-[9px] font-black text-slate-400 ${logo ? 'hidden' : 'flex'}`}
            >
                {abbr || '??'}
            </span>
        </div>
    );
}

function InjuryPills({ injuries = [] }) {
    const outStatuses = ['out', 'doubtful', 'questionable', 'day-to-day'];
    const relevant = injuries.filter(i => outStatuses.some(s => (i.status || '').toLowerCase().includes(s)));
    if (relevant.length === 0) return null;

    return (
        <div className="flex flex-wrap gap-1 mt-1">
            {relevant.slice(0, 3).map((inj, idx) => (
                <span
                    key={idx}
                    title={inj.short_comment || inj.status}
                    className="text-[7px] font-black uppercase px-1.5 py-0.5 rounded border bg-rose-950/40 text-rose-400 border-rose-500/25 truncate max-w-[100px]"
                >
                    🏥 {inj.name?.split(' ').pop() || 'Player'} — {inj.status}
                </span>
            ))}
            {relevant.length > 3 && (
                <span className="text-[7px] font-black text-slate-500">+{relevant.length - 3} more</span>
            )}
        </div>
    );
}

function EloStandingsPanel({ standings = [] }) {
    if (!standings.length) return null;
    const top = standings.slice(0, 5);

    return (
        <div className="bg-slate-900/35 border border-slate-850/60 rounded-3xl p-5 shadow-inner">
            <div className="flex items-center justify-between mb-4">
                <span className="text-[9px] font-black uppercase tracking-widest text-slate-500">🏆 ELO Power Rankings</span>
                <span className="text-[8px] font-bold text-slate-600">Top 5</span>
            </div>
            <div className="space-y-2">
                {top.map((team, idx) => (
                    <div key={team.team_id} className="flex items-center justify-between text-[10px] border-b border-slate-900/40 pb-2 last:border-0 last:pb-0">
                        <div className="flex items-center gap-2">
                            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-black border
                                ${idx === 0 ? 'bg-amber-950/50 text-amber-400 border-amber-500/30' : 'bg-slate-950 text-slate-500 border-slate-800'}`}>
                                {idx + 1}
                            </span>
                            <span className="font-black text-slate-300">{team.team_abbr}</span>
                        </div>
                        <span className="font-black text-indigo-400 tabular-nums">{team.elo}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────
//  Match Card
// ─────────────────────────────────────────────────────────────

function WnbaMatchCard({ predict, injuriesByTeam = {}, isResultCard = false, resultMeta = null }) {
    const [expanded, setExpanded] = useState(false);
    const [statsExpanded, setStatsExpanded] = useState(false);

    const hasOdds = predict.odds && predict.odds.moneyline_home != null && predict.odds.moneyline_away != null;
    const homeWinProb = Math.round((predict.home_win_prob || 0) * 100);
    const awayWinProb = Math.round((predict.away_win_prob || 0) * 100);

    const highConfAlt = (predict.alt_bets || []).filter(b => b.confidence === 'High' || b.confidence === 'Medium');
    const hasHighConf = (predict.alt_bets || []).some(b => b.confidence === 'High');

    const homeInjuries = injuriesByTeam[predict.home_team_id] || [];
    const awayInjuries = injuriesByTeam[predict.away_team_id] || [];
    const starImpact = predict.features?.feature_star_out_impact_diff;

    return (
        <div
            className={`relative rounded-3xl p-5 flex flex-col gap-4 transition-all duration-300 shadow-lg group overflow-hidden
                ${hasHighConf
                    ? 'bg-slate-900/35 border border-indigo-500/30 hover:border-indigo-400/50 shadow-[0_0_20px_rgba(99,102,241,0.07)]'
                    : 'bg-slate-900/30 border border-slate-850 hover:border-slate-800'
                }`}
        >
            {hasHighConf && (
                <div className="absolute inset-0 pointer-events-none rounded-3xl bg-gradient-to-br from-indigo-500/[0.04] to-transparent" />
            )}

            {/* Header */}
            <div className="flex justify-between items-start border-b border-slate-950/60 pb-3 gap-2 relative z-10">
                <div className="flex flex-col min-w-0">
                    <span className="text-[10px] text-indigo-400 font-black uppercase tracking-wider block">
                        🏀 WNBA Match Projection
                    </span>
                    <span className="text-[9px] text-slate-500 font-bold mt-1 uppercase truncate max-w-[220px] sm:max-w-none">
                        🏟️ {predict.venue || 'TBD'} • {predict.date}
                    </span>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                    {isResultCard && resultMeta && (
                        <span className={`text-[8px] font-black uppercase tracking-widest px-2 py-0.5 rounded border
                            ${resultMeta.ml_correct ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30' : 'bg-rose-950/60 text-rose-400 border-rose-500/30'}`}>
                            {resultMeta.ml_correct ? '✓ ML Correct' : '✗ ML Wrong'}
                        </span>
                    )}
                    {predict.bet_count > 0 && !isResultCard && (
                        <span className="text-[8px] font-black text-emerald-400 bg-emerald-950/50 border border-emerald-500/20 px-2.5 py-1 rounded-full animate-pulse uppercase tracking-wider">
                            🔥 {predict.bet_count} Plays
                        </span>
                    )}
                    <span className="text-[8px] text-slate-500 font-extrabold uppercase tracking-widest bg-slate-950/50 border border-slate-850 px-2 py-1 rounded">
                        #{predict.game_id?.slice(-4)}
                    </span>
                </div>
            </div>

            {/* Teams */}
            <div className="space-y-3 relative z-10">
                {/* Away */}
                <div className="flex justify-between items-center gap-2">
                    <div className="flex items-center gap-3 min-w-0">
                        <TeamLogo logo={predict.away_logo} abbr={predict.away_team_abbr} />
                        <div className="min-w-0">
                            <div className={`text-xs font-black truncate ${predict.predicted_winner_abbr === predict.away_team_abbr ? 'text-indigo-400' : 'text-gray-300'}`}>
                                {predict.away_team_name} {predict.predicted_winner_abbr === predict.away_team_abbr && '🎯'}
                            </div>
                            <div className="text-[9px] text-slate-500 font-bold">
                                ELO {predict.elo_away || '1500'} • Rest {predict.rest_away != null ? `${predict.rest_away}d` : '—'}
                            </div>
                            <InjuryPills injuries={awayInjuries} />
                        </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                        <div className="text-xs font-black text-gray-300">{awayWinProb}%</div>
                        {hasOdds && (
                            <span className="text-[8px] font-bold text-slate-500 bg-slate-950/60 border border-slate-900/80 px-1 py-0.5 rounded">
                                {displayAmericanOdds(predict.odds.moneyline_away)}
                            </span>
                        )}
                    </div>
                </div>

                {/* Probability bar */}
                <div className="w-full bg-slate-950/80 rounded-full h-2 border border-slate-900/60 overflow-hidden flex shadow-inner">
                    <div className="h-full bg-slate-800 rounded-l-full transition-all duration-700" style={{ width: `${awayWinProb}%` }} />
                    <div
                        className="h-full bg-gradient-to-r from-indigo-500 to-cyan-500 rounded-r-full shadow-[0_0_8px_rgba(99,102,241,0.4)] transition-all duration-700"
                        style={{ width: `${homeWinProb}%` }}
                    />
                </div>

                {/* Home */}
                <div className="flex justify-between items-center gap-2">
                    <div className="flex items-center gap-3 min-w-0">
                        <TeamLogo logo={predict.home_logo} abbr={predict.home_team_abbr} />
                        <div className="min-w-0">
                            <div className={`text-xs font-black truncate ${predict.predicted_winner_abbr === predict.home_team_abbr ? 'text-indigo-400' : 'text-gray-300'}`}>
                                {predict.home_team_name} {predict.predicted_winner_abbr === predict.home_team_abbr && '🎯'}
                            </div>
                            <div className="text-[9px] text-slate-500 font-bold">
                                ELO {predict.elo_home || '1500'} • Rest {predict.rest_home != null ? `${predict.rest_home}d` : '—'}
                            </div>
                            <InjuryPills injuries={homeInjuries} />
                        </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                        <div className="text-xs font-black text-gray-300">{homeWinProb}%</div>
                        {hasOdds && (
                            <span className="text-[8px] font-bold text-slate-500 bg-slate-950/60 border border-slate-900/80 px-1 py-0.5 rounded">
                                {displayAmericanOdds(predict.odds.moneyline_home)}
                            </span>
                        )}
                    </div>
                </div>
            </div>

            {/* Result score */}
            {isResultCard && resultMeta?.actual_score && (
                <div className="bg-slate-950/50 border border-slate-900 rounded-2xl px-4 py-2 text-center relative z-10">
                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Final Score</span>
                    <span className="text-sm font-black text-white tabular-nums">{resultMeta.actual_score}</span>
                </div>
            )}

            {/* Projections */}
            <div className="grid grid-cols-3 gap-2 bg-slate-950/60 border border-slate-900 rounded-2xl p-3.5 shadow-inner relative z-10">
                <div className="text-center border-r border-slate-900/60 pr-2">
                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Winner</span>
                    <span className="text-[10px] font-black text-white mt-1 block truncate">
                        {predict.predicted_winner_abbr} ({Math.max(homeWinProb, awayWinProb)}%)
                    </span>
                </div>
                <div className="text-center border-r border-slate-900/60 px-2">
                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Spread</span>
                    <span className="text-[10px] font-black text-cyan-400 mt-1 block">
                        {formatSignedValue(predict.predicted_spread)}
                        {predict.odds?.spread_line != null && (
                            <span className="text-[8px] text-slate-500 ml-1 font-bold">({formatSignedValue(predict.odds.spread_line)})</span>
                        )}
                    </span>
                </div>
                <div className="text-center pl-2">
                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Total</span>
                    <span className="text-[10px] font-black text-indigo-400 mt-1 block">
                        {predict.predicted_total?.toFixed(1)}
                        {predict.odds?.total_line != null && (
                            <span className="text-[8px] text-slate-500 ml-1 font-bold">({predict.odds.total_line})</span>
                        )}
                    </span>
                </div>
            </div>

            {starImpact != null && Math.abs(starImpact) >= 0.5 && (
                <div className="text-[9px] font-bold text-amber-400/90 bg-amber-950/20 border border-amber-500/20 rounded-xl px-3 py-2 relative z-10">
                    ⭐ Star absence impact (home − away PPG): {formatSignedValue(starImpact)}
                </div>
            )}

            {/* Röntgen accordion */}
            <div className="border-t border-slate-900/70 pt-3 relative z-10">
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="w-full flex items-center justify-between cursor-pointer focus:outline-none group/acc"
                >
                    <span className="flex items-center gap-1.5 text-[9px] font-black uppercase tracking-widest text-slate-400 group-hover/acc:text-indigo-300 transition-colors flex-wrap">
                        <span className={hasHighConf ? 'text-indigo-400' : ''}>⚡</span>
                        Röntgen &amp; AI Edge
                        {predict.alt_bets?.length > 0 && (
                            <span className={`px-1.5 py-0.5 rounded text-[8px] font-black border ${hasHighConf ? 'bg-indigo-950/60 text-indigo-400 border-indigo-500/30' : 'bg-slate-900 text-slate-500 border-slate-800'}`}>
                                {predict.alt_bets.length} Markets
                            </span>
                        )}
                        {predict.ai_insight && (
                            <span className="text-[8px] font-black text-cyan-400 bg-cyan-950/50 border border-cyan-500/20 px-1.5 py-0.5 rounded uppercase">
                                💡 Insight
                            </span>
                        )}
                    </span>
                    <span className="text-[9px] text-slate-500 group-hover/acc:text-slate-300 transition-colors font-bold">
                        {expanded ? '▲' : '▼'}
                    </span>
                </button>

                {expanded && (
                    <div className="mt-4 space-y-4 animate-fade-in">
                        {predict.ai_insight && (
                            <div className="space-y-1.5">
                                <span className="text-[7.5px] font-black uppercase tracking-widest text-slate-500 block">🧠 AI Edge Insight</span>
                                {renderAiInsight(predict.ai_insight)}
                            </div>
                        )}

                        {predict.alt_bets?.length > 0 && (
                            <div className="space-y-2">
                                <span className="text-[8px] font-black uppercase tracking-widest text-slate-500 block">🎯 Model-Implied Value Plays</span>
                                <div className="space-y-2">
                                    {[...predict.alt_bets].sort((a, b) => {
                                        const order = { High: 0, Medium: 1, Low: 2 };
                                        return (order[a.confidence] ?? 2) - (order[b.confidence] ?? 2);
                                    }).map((bet, idx) => {
                                        const conf = bet.confidence || 'Low';
                                        const isHigh = conf === 'High';
                                        const isMed = conf === 'Medium';
                                        return (
                                            <div
                                                key={idx}
                                                className={`rounded-2xl p-3 flex justify-between items-center gap-3 border
                                                    ${isHigh ? 'bg-indigo-950/30 border-indigo-500/25' : isMed ? 'bg-amber-950/20 border-amber-500/20' : 'bg-slate-950/40 border-slate-900'}`}
                                            >
                                                <div>
                                                    <div className="text-xs font-black text-white">{bet.pick}</div>
                                                    <div className="text-[8px] text-slate-500 font-bold uppercase mt-0.5">
                                                        {bet.market} • {bet.model_prediction || bet.model_win_prob || ''}
                                                    </div>
                                                </div>
                                                <div className="text-right">
                                                    <div className="text-xs font-black text-emerald-400">+{bet.edge?.toFixed(1)}% Edge</div>
                                                    <span className={`text-[7px] font-black uppercase px-1.5 py-0.5 rounded
                                                        ${isHigh ? 'bg-emerald-950 text-emerald-400' : isMed ? 'bg-amber-950 text-amber-500' : 'bg-slate-900 text-slate-500'}`}>
                                                        {conf} Conf
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        <div className="space-y-2">
                            <button
                                onClick={() => setStatsExpanded(!statsExpanded)}
                                className="w-full flex items-center justify-between bg-slate-950/60 border border-slate-900 hover:border-slate-850 rounded-xl px-3 py-2 text-[9px] font-black uppercase tracking-wider text-slate-400 hover:text-white transition-all"
                            >
                                <span>📈 Form &amp; Sabermetric Comparison</span>
                                <span>{statsExpanded ? '▲ CLOSE' : '▼ OPEN'}</span>
                            </button>

                            {statsExpanded && predict.home_l5 && predict.away_l5 && (
                                <div className="bg-slate-950/80 border border-slate-900 rounded-2xl p-4 overflow-x-auto">
                                    <table className="w-full text-xs font-semibold border-collapse text-slate-300">
                                        <thead>
                                            <tr className="border-b border-slate-900 text-[8px] font-black uppercase tracking-wider text-slate-500">
                                                <th className="py-2 text-left">Metric (L5)</th>
                                                <th className="py-2 text-center">{predict.away_team_abbr}</th>
                                                <th className="py-2 text-center">{predict.home_team_abbr}</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-900/60">
                                            {[
                                                { name: 'PPG', home: predict.home_l5.ppg?.toFixed(1), away: predict.away_l5.ppg?.toFixed(1) },
                                                { name: 'OPPG', home: predict.home_l5.oppg?.toFixed(1), away: predict.away_l5.oppg?.toFixed(1) },
                                                { name: 'Net Rating', home: predict.home_l5.net_rtg?.toFixed(1), away: predict.away_l5.net_rtg?.toFixed(1) },
                                                { name: 'Off Rating', home: predict.home_l5.ortg?.toFixed(1), away: predict.away_l5.ortg?.toFixed(1) },
                                                { name: 'Def Rating', home: predict.home_l5.drtg?.toFixed(1), away: predict.away_l5.drtg?.toFixed(1) },
                                                { name: 'Pace', home: predict.home_l5.pace?.toFixed(1), away: predict.away_l5.pace?.toFixed(1) },
                                                { name: 'TS%', home: `${(predict.home_l5.ts_pct * 100).toFixed(1)}%`, away: `${(predict.away_l5.ts_pct * 100).toFixed(1)}%` },
                                                { name: 'Win Rate L5', home: `${(predict.home_l5.win_rate * 100).toFixed(0)}%`, away: `${(predict.away_l5.win_rate * 100).toFixed(0)}%` },
                                            ].map((row, rIdx) => (
                                                <tr key={rIdx} className="hover:bg-slate-900/35 transition-colors">
                                                    <td className="py-2 text-slate-400 font-bold">{row.name}</td>
                                                    <td className="py-2 text-center tabular-nums">{row.away}</td>
                                                    <td className="py-2 text-center tabular-nums">{row.home}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>

                        {predict.h2h_last10?.length > 0 && (
                            <div className="space-y-2">
                                <span className="text-[8px] font-black uppercase tracking-widest text-slate-500 block">📊 Head-to-Head (Last 10)</span>
                                <div className="bg-slate-950/40 border border-slate-900 rounded-2xl p-3 overflow-x-auto">
                                    <table className="w-full text-[10px] font-bold text-slate-400 text-center border-collapse">
                                        <thead>
                                            <tr className="border-b border-slate-900 text-[8px] font-black uppercase text-slate-500">
                                                <th className="pb-1.5 text-left">Date</th>
                                                <th className="pb-1.5">Matchup</th>
                                                <th className="pb-1.5">Score</th>
                                                <th className="pb-1.5 text-right">Winner</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-900/40">
                                            {predict.h2h_last10.map((h2h, hIdx) => (
                                                <tr key={hIdx}>
                                                    <td className="py-2 text-left text-slate-500 font-semibold">{h2h.date}</td>
                                                    <td className="py-2">{h2h.away_team} @ {h2h.home_team}</td>
                                                    <td className="py-2 text-slate-300 font-black tabular-nums">{h2h.score}</td>
                                                    <td className="py-2 text-right text-indigo-400 font-extrabold">{h2h.winner}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────
//  Main Dashboard
// ─────────────────────────────────────────────────────────────

function WnbaDashboard({ selectedDate }) {
    const { data, loading, error, isPreparing } = useWnbaPredictions(selectedDate);
    const [matchView, setMatchView] = useState('upcoming');

    if (error && !data) {
        return (
            <div className="bg-rose-950/30 border border-rose-500/30 rounded-3xl p-8 text-center max-w-xl mx-auto my-10 animate-fade-in">
                <span className="text-4xl block mb-3">⚠️</span>
                <h3 className="text-base font-black text-rose-400 uppercase tracking-widest mb-2">API Connection Error</h3>
                <p className="text-xs text-slate-300 leading-relaxed font-semibold">{error}</p>
            </div>
        );
    }

    if (isPreparing) {
        return (
            <div className="bg-slate-900/60 backdrop-blur-xl border border-indigo-500/30 rounded-3xl p-8 text-center max-w-md mx-auto my-10 shadow-[0_0_50px_rgba(99,102,241,0.15)] flex flex-col items-center">
                <div className="relative mb-6">
                    <span className="text-6xl inline-block animate-spin [animation-duration:3s]">🏀</span>
                    <div className="absolute inset-0 rounded-full bg-indigo-500/10 blur-xl animate-pulse" />
                </div>
                <h2 className="text-lg font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-indigo-400 uppercase tracking-widest mb-3">
                    Waking Up WNBA Engine
                </h2>
                <p className="text-slate-300 text-xs font-semibold leading-relaxed mb-6">
                    The backend is preparing today&apos;s WNBA predictions. ELO models, injury feed, and odds will load in about 30 seconds.
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

    if (loading && !data) {
        return (
            <div className="space-y-8 animate-pulse">
                <div className="h-28 bg-slate-900/40 border border-slate-850 rounded-3xl" />
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map(i => <div key={i} className="h-20 bg-slate-900/30 border border-slate-850 rounded-2xl" />)}
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {[1, 2].map(i => <div key={i} className="h-64 bg-slate-900/30 border border-slate-850 rounded-3xl" />)}
                </div>
            </div>
        );
    }

    const payload = data?.predictions || {};
    const predictions = payload.predictions || [];
    const modelMeta = payload.model_meta || {};
    const betaVersion = payload.beta_version || modelMeta.beta_version || '1.0.0-beta';
    const results = data?.results || null;
    const lastUpdated = data?.last_updated || 'Unknown';
    const injuriesByTeam = data?.injuries?.by_team || {};
    const standings = data?.standings || [];

    const resultMap = {};
    (results?.results || []).forEach(r => {
        if (r.game_id) resultMap[r.game_id] = r;
    });

    const hasResults = results && (results.ml_total || 0) > 0;
    const resultItems = (results?.results || []).map(r => {
        const pred = predictions.find(p => p.game_id === r.game_id);
        return { result: r, prediction: pred };
    }).filter(item => item.prediction || item.result);

    const totalPlays = predictions.reduce((sum, p) => sum + (p.bet_count || 0), 0);

    return (
        <div className="space-y-7 animate-fade-in pb-12 selection:bg-indigo-500 selection:text-white">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/40 border border-slate-850 p-5 sm:p-6 rounded-3xl backdrop-blur-xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-48 h-48 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />
                <div className="space-y-1.5 relative z-10 text-center md:text-left">
                    <div className="flex items-center justify-center md:justify-start gap-2.5 flex-wrap">
                        <span className="text-2xl sm:text-3xl">🏀</span>
                        <h2 className="text-lg sm:text-xl md:text-2xl font-black text-white uppercase tracking-wider">
                            WNBA Match Projections
                        </h2>
                        <span className="text-[9px] font-black tracking-widest text-cyan-400 bg-cyan-950/50 border border-cyan-500/30 px-2 py-0.5 rounded-md uppercase">
                            BETA
                        </span>
                        <span className="text-[8px] font-bold text-slate-500 bg-slate-950/60 border border-slate-800 px-2 py-0.5 rounded">
                            v{betaVersion}
                        </span>
                    </div>
                    <p className="text-xs text-slate-400 font-semibold max-w-2xl leading-relaxed mx-auto md:mx-0">
                        XGBoost + Optuna models tuned for WNBA pace, ELO, rest fatigue, star absence, and team offensive/defensive ratings.
                    </p>
                </div>
                <div className="flex flex-col items-center md:items-end justify-center self-center md:self-auto text-center md:text-right relative z-10">
                    <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">Last Updated (ET)</span>
                    <span className="text-xs text-slate-300 font-extrabold mt-0.5 bg-slate-950/40 border border-slate-850 px-3 py-1 rounded-lg">
                        ⏱️ {lastUpdated.split(' ')[1] || lastUpdated}
                    </span>
                </div>
            </div>

            {/* Model stats strip */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                    { label: 'Today\'s Games', value: predictions.length, color: 'text-white' },
                    { label: 'Win Model Acc.', value: formatPct(modelMeta.win_accuracy), color: 'text-emerald-400' },
                    { label: 'Value Plays', value: totalPlays, color: 'text-indigo-400' },
                    { label: 'Features', value: modelMeta.win_feature_count || '—', color: 'text-cyan-400' },
                ].map(({ label, value, color }) => (
                    <div key={label} className="bg-slate-900/35 border border-slate-850/60 rounded-2xl p-4 text-center shadow-inner">
                        <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">{label}</span>
                        <span className={`text-lg font-black block mt-1 ${color}`}>{value}</span>
                    </div>
                ))}
            </div>

            {/* Accuracy card */}
            {hasResults && (
                <div className="bg-emerald-950/15 border border-emerald-500/20 rounded-3xl p-5 md:p-6 shadow-[0_10px_35px_rgba(16,185,129,0.05)] relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none" />
                    <div className="flex flex-col md:flex-row items-center justify-between gap-5 relative z-10">
                        <div className="space-y-1 text-center md:text-left">
                            <span className="text-[9px] text-emerald-400 font-black uppercase tracking-widest bg-emerald-950/60 border border-emerald-500/25 px-2.5 py-0.5 rounded-full">
                                ✓ Live Accuracy Verification
                            </span>
                            <h4 className="text-sm md:text-base font-black text-white tracking-wider uppercase mt-1">Model Performance</h4>
                            <p className="text-xs text-slate-400 font-medium leading-relaxed max-w-xl">
                                Tracked across {results.games_evaluated || results.ml_total} finished games.
                            </p>
                        </div>
                        <div className="grid grid-cols-3 gap-3 w-full md:w-auto text-center">
                            {[
                                { label: 'Moneyline', acc: results.ml_accuracy, correct: results.ml_correct, total: results.ml_total, color: 'text-emerald-400' },
                                { label: 'Spread', acc: results.spread_accuracy, correct: results.spread_correct, total: results.spread_total, color: 'text-cyan-400' },
                                { label: 'Total', acc: results.total_accuracy, correct: results.total_correct, total: results.total_total, color: 'text-indigo-400' },
                            ].map(({ label, acc, correct, total, color }) => (
                                <div key={label} className="bg-slate-950/50 border border-slate-900 rounded-2xl p-3 min-w-[90px]">
                                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">{label}</span>
                                    <span className={`text-base font-black block mt-0.5 ${color}`}>
                                        {acc != null ? `${(acc * 100).toFixed(0)}%` : '—'}
                                    </span>
                                    <span className="text-[8px] text-slate-500 font-bold block mt-0.5">
                                        {correct ?? 0}/{total ?? 0}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* ELO + View tabs row */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
                <div className="lg:col-span-3 space-y-5">
                    <div className="flex items-center gap-1 p-1 bg-slate-950/70 border border-slate-900 rounded-2xl w-full sm:w-max shadow-inner">
                        <button
                            onClick={() => setMatchView('upcoming')}
                            className={`px-4 py-2 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all cursor-pointer
                                ${matchView === 'upcoming'
                                    ? 'bg-gradient-to-br from-indigo-600/90 to-blue-600/90 text-white shadow-[0_0_15px_rgba(99,102,241,0.3)] border border-indigo-400/40'
                                    : 'text-slate-400 hover:text-slate-200 border border-transparent'
                                }`}
                        >
                            📅 Upcoming ({predictions.length})
                        </button>
                        <button
                            onClick={() => setMatchView('results')}
                            className={`px-4 py-2 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all cursor-pointer
                                ${matchView === 'results'
                                    ? 'bg-gradient-to-br from-emerald-600/90 to-teal-600/90 text-white shadow-[0_0_15px_rgba(16,185,129,0.3)] border border-emerald-400/40'
                                    : 'text-slate-400 hover:text-slate-200 border border-transparent'
                                }`}
                        >
                            ✅ Results ({resultItems.length})
                        </button>
                    </div>

                    {matchView === 'upcoming' && (
                        predictions.length === 0 ? (
                            <div className="bg-slate-900/20 border border-dashed border-slate-850 rounded-3xl p-12 text-center max-w-lg mx-auto animate-fade-in select-none">
                                <span className="text-4xl block mb-3">📭</span>
                                <h4 className="text-sm font-black text-slate-400 uppercase tracking-widest">No Matches Calculated</h4>
                                <p className="text-[10px] text-slate-500 font-semibold mt-2">
                                    There are no upcoming WNBA matches calculated for this date.
                                </p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                                {predictions.map(predict => (
                                    <WnbaMatchCard
                                        key={predict.game_id}
                                        predict={predict}
                                        injuriesByTeam={injuriesByTeam}
                                    />
                                ))}
                            </div>
                        )
                    )}

                    {matchView === 'results' && (
                        resultItems.length === 0 ? (
                            <div className="bg-slate-900/20 border border-dashed border-slate-850 rounded-3xl p-12 text-center max-w-lg mx-auto animate-fade-in select-none">
                                <span className="text-4xl block mb-3">⏳</span>
                                <h4 className="text-sm font-black text-slate-400 uppercase tracking-widest">No Results Yet</h4>
                                <p className="text-[10px] text-slate-500 font-semibold mt-2">
                                    Finished games will appear here once box scores are synced.
                                </p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                                {resultItems.map(({ result, prediction }) => (
                                    <WnbaMatchCard
                                        key={result.game_id}
                                        predict={prediction || {
                                            game_id: result.game_id,
                                            name: result.name,
                                            home_team_abbr: result.home_team_abbr,
                                            away_team_abbr: result.away_team_abbr,
                                            predicted_winner_abbr: result.predicted_winner_abbr,
                                            home_win_prob: result.home_win_prob || 0.5,
                                            away_win_prob: 1 - (result.home_win_prob || 0.5),
                                        }}
                                        injuriesByTeam={injuriesByTeam}
                                        isResultCard
                                        resultMeta={result}
                                    />
                                ))}
                            </div>
                        )
                    )}
                </div>

                <div className="lg:col-span-1">
                    <EloStandingsPanel standings={standings} />
                </div>
            </div>
        </div>
    );
}

export default WnbaDashboard;
