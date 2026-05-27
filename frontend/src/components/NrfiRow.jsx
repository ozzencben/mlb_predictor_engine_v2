import React, { useState } from 'react';
import { getTeamLogo, formatAmericanOdds, getTeamAbbr } from '../utils/formatters';
import SportsbookLogo from './SportsbookLogo';
import CountUp from './CountUp';
import CircularProgress from './CircularProgress';
import { formatAiInsight } from '../utils/textFormatter';

const getNrfiColor = (pct) => {
    if (pct === 'N/A' || !pct) return 'bg-slate-800 text-gray-500 border-slate-700';
    if (pct >= 70) return 'bg-red-500/20 text-red-400 border-red-500/30'; // Hot
    if (pct <= 40) return 'bg-blue-500/20 text-blue-400 border-blue-500/30'; // Cold
    return 'bg-slate-700 text-gray-300 border-slate-600'; // Neutral
};

const renderNrfiStat = (pct, record, isFallback) => {
    if (isFallback) {
        return (
            <span className="text-[8px] font-bold text-slate-600 italic">N/A</span>
        );
    }
    if (pct === 'N/A' || pct === undefined || pct === null) return <span className="text-slate-400 font-bold text-xs">-</span>;
    return (
        <div className="flex flex-col items-center justify-center">
            <span className={`px-1.5 py-0.5 rounded text-[10px] md:text-xs font-black border tracking-wider shadow-sm ${getNrfiColor(pct)}`}>
                <CountUp end={pct} decimals={1} suffix="%" />
            </span>
            {record && record !== "0-0" && <span className="text-[8px] md:text-[9px] text-gray-400 font-bold mt-1 tracking-wider whitespace-nowrap">{record}</span>}
        </div>
    );
};

const NrfiRow = ({ prediction }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const { matchup, NRFI, Details, Weather } = prediction;
    const trends = NRFI?.scraped_trends || {};
    const isFallback = trends?.is_fallback === true;
    const awayTrends = trends?.away_pitcher || {};
    const homeTrends = trends?.home_pitcher || {};
    const awayTeamNrfi = trends?.away_team_nrfi || {};
    const homeTeamNrfi = trends?.home_team_nrfi || {};
    const aiInsight = Details?.ai_insight;

    // Atıcının bu sezon verisi yoksa (Lig Ort. ile doldurulmuş)
    const awayPitcherNoData = awayTrends?.season_record === '0-0' && !isFallback;
    const homePitcherNoData = homeTrends?.season_record === '0-0' && !isFallback;
    const Odds = prediction.Odds || {};
    const hasNrfiOdds = !!(Odds.nrfi_odds && Odds.nrfi_odds !== 0.0);

    // AI/Algo Score
    const nrfiScore = (NRFI?.nrfi_score * 100).toFixed(1);
    const yrfiScore = (NRFI?.yrfi_score * 100).toFixed(1);
    const pick = NRFI?.pick;

    const isNrfiFavored = NRFI?.nrfi_score >= NRFI?.yrfi_score;
    const scoreColor = isNrfiFavored ? "text-green-400 bg-green-500/10 border-green-500/30" : "text-red-400 bg-red-500/10 border-red-500/30";

    return (
        <div id={`nrfi-card-${matchup.away_team}-${matchup.home_team}`} className="bg-slate-900/40 backdrop-blur-xl border border-slate-700/60 shadow-[0_8px_32px_rgba(0,0,0,0.37)] rounded-2xl overflow-hidden mb-3 md:mb-4 transition-all duration-500 hover:-translate-y-0.5 hover:border-indigo-500/50 hover:shadow-[0_12px_24px_rgba(99,102,241,0.15)] w-full relative">

            {/* ABSOLUTE TIME BADGE (Kartın Sol Üstüne Taşındı) */}
            <div className="absolute top-0 left-0 bg-slate-800/80 backdrop-blur-sm border-b border-r border-gray-700 px-2.5 py-1 rounded-br-lg z-10 flex items-center justify-center shadow-sm">
                <span className="text-[9px] font-black text-gray-300 tracking-wider whitespace-nowrap">
                    🕒 {matchup.game_time || "TBD"}
                </span>
            </div>

            {/* Header / Summary Row */}
            {/* Mobilde yukardan biraz boşluk (pt-7) verdik çünkü sol üstte saat badge'i var */}
            <div className="p-3 pt-7 md:pt-4 md:p-4 flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4">

                {/* Team Matchup & Logos */}
                <div className="flex items-center gap-2 xs:gap-3 w-full sm:w-auto flex-1 justify-center sm:justify-start mt-1 sm:mt-0">
                    <div className="flex items-center gap-1.5 xs:gap-2">
                        <img src={getTeamLogo(matchup.away_team)} alt={matchup.away_team} className="w-7 h-7 xs:w-8 xs:h-8 md:w-10 md:h-10 drop-shadow-md flex-shrink-0" loading="lazy" width="40" height="40" />
                        <span className="text-[11px] xs:text-xs md:text-sm font-black text-white hidden xs:inline">{matchup.away_team}</span>
                        <span className="text-[11px] xs:text-xs md:text-sm font-black text-white xs:hidden">{getTeamAbbr(matchup.away_team)}</span>
                    </div>
                    <span className="text-[9px] md:text-xs font-black text-slate-400 flex-shrink-0">@</span>
                    <div className="flex items-center gap-1.5 xs:gap-2">
                        <img src={getTeamLogo(matchup.home_team)} alt={matchup.home_team} className="w-7 h-7 xs:w-8 xs:h-8 md:w-10 md:h-10 drop-shadow-md flex-shrink-0" loading="lazy" width="40" height="40" />
                        <span className="text-[11px] xs:text-xs md:text-sm font-black text-white hidden xs:inline">{matchup.home_team}</span>
                        <span className="text-[11px] xs:text-xs md:text-sm font-black text-white xs:hidden">{getTeamAbbr(matchup.home_team)}</span>
                    </div>
                </div>

                {/* Info Blocks & Button Group */}
                <div className="flex flex-row items-center gap-2 sm:gap-4 w-full sm:w-auto">

                    {/* Vegas Odds Block */}
                    {hasNrfiOdds ? (
                        <div className="bg-slate-900/50 border border-slate-800/60 p-1.5 xs:p-2 sm:p-2.5 rounded-lg flex flex-col items-center justify-center flex-1 sm:flex-none">
                            <span className="text-[7px] md:text-[8px] text-slate-400 font-bold uppercase tracking-widest mb-0.5">Vegas</span>
                            <div className="flex items-center gap-1.5 md:gap-2">
                                <div className="flex flex-col items-center">
                                    <span className={`text-[9px] xs:text-[10px] md:text-xs font-black leading-tight ${Odds.nrfi_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-300'}`}>
                                        N {formatAmericanOdds(Odds.nrfi_odds)}
                                    </span>
                                </div>
                                <span className="text-[8px] md:text-[10px] font-black text-gray-700 flex-shrink-0">|</span>
                                <div className="flex flex-col items-center">
                                    <span className={`text-[9px] xs:text-[10px] md:text-xs font-black leading-tight ${Odds.yrfi_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-300'}`}>
                                        Y {formatAmericanOdds(Odds.yrfi_odds)}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="bg-slate-900/50 border border-slate-800/60 p-1.5 xs:p-2 sm:p-2.5 rounded-lg flex flex-col items-center justify-center flex-1 sm:flex-none">
                            <span className="text-[7px] md:text-[8px] text-slate-400 font-bold uppercase tracking-widest mb-0.5">Vegas</span>
                            <span className="text-[8px] xs:text-[9px] font-black text-amber-500 px-1.5 py-0.5 rounded whitespace-nowrap">
                                🔒 Locked
                            </span>
                        </div>
                    )}

                    {/* AI Score Block (with beautiful neon Circular Progress) */}
                    <div className="bg-slate-900/40 backdrop-blur-md border border-slate-800/60 p-1.5 xs:p-2 rounded-xl flex items-center gap-2 flex-1 sm:flex-none shadow-inner relative">
                        <CircularProgress percentage={isNrfiFavored ? nrfiScore : yrfiScore} size={36} strokeWidth={3} />
                        <div className="flex flex-col items-start justify-center">
                            <div className="text-[7px] md:text-[8px] text-slate-400 font-extrabold uppercase tracking-widest leading-none mb-1 flex items-center gap-1">
                                <span>AI Pick</span>
                                {parseFloat(isNrfiFavored ? nrfiScore : yrfiScore) >= 70 && (
                                    <span className="text-[10px] leading-none text-amber-400 animate-bounce">👑</span>
                                )}
                            </div>
                            <span className={`px-1.5 py-0.5 rounded border text-[9px] xs:text-[10px] md:text-xs font-black leading-none whitespace-nowrap ${scoreColor}`}>
                                {pick}
                            </span>
                        </div>
                    </div>

                    {/* Minimal Expand Button */}
                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="bg-blue-600 hover:bg-blue-500 text-white rounded-lg p-2 xs:p-2.5 sm:px-4 sm:py-2 flex items-center justify-center transition-all shadow-md active:scale-95 flex-shrink-0 h-[38px] sm:h-[46px]"
                        aria-label={isExpanded ? "Hide Details" : "Show Details"}
                    >
                        <span className="hidden sm:block text-xs font-bold mr-1.5">{isExpanded ? "Hide" : "Details"}</span>
                        <svg className={`w-3.5 h-3.5 xs:w-4 xs:h-4 sm:w-3 sm:h-3 transition-transform ${isExpanded ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M19 9l-7 7-7-7"></path></svg>
                    </button>
                </div>
            </div>

            {/* Smooth Dropdown Detail View (CSS Grid Accordion) */}
            <div className={`grid transition-all duration-500 ease-in-out ${isExpanded ? 'grid-rows-[1fr] opacity-100 border-t border-gray-700/50 bg-slate-900/20' : 'grid-rows-[0fr] opacity-0 pointer-events-none'}`}>
                <div className="overflow-hidden">
                    <div className="p-3 md:p-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* LEFT: Pitcher & Team NRFI Records */}
                            <div className="flex flex-col gap-3">
                                <h3 className="text-[10px] text-gray-400 font-bold uppercase tracking-widest border-b border-slate-700 pb-1 flex items-center gap-2">
                                    Pitcher NRFI Trends
                                    {isFallback && (
                                        <span className="text-[7px] font-black text-amber-500 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded uppercase tracking-wider">⚠️ No Trend Data</span>
                                    )}
                                </h3>
                                <div className="bg-slate-800/50 rounded-lg p-2 border border-slate-700/50">
                                    <div className="grid grid-cols-[1.8fr_1fr_1fr_1fr] gap-2 text-center items-center mb-2">
                                        <div className="text-left text-[8px] md:text-[9px] font-black text-slate-400 uppercase">Pitcher</div>
                                        <div className="text-[8px] md:text-[9px] font-black text-slate-400 uppercase">Season</div>
                                        <div className="text-[8px] md:text-[9px] font-black text-slate-400 uppercase">Loc</div>
                                        <div className="text-[8px] md:text-[9px] font-black text-slate-400 uppercase">L10</div>
                                    </div>
                                    <div className="grid grid-cols-[1.8fr_1fr_1fr_1fr] gap-2 text-center items-center mb-2 border-b border-slate-700/30 pb-2">
                                        <div className="text-left text-[9px] md:text-[10px] font-bold text-gray-300 truncate pr-1 flex flex-col gap-0.5">
                                            {matchup.away_pitcher}
                                            {awayPitcherNoData && <span className="text-[7px] font-black text-amber-500/80 bg-amber-500/10 border border-amber-500/20 px-1 py-0.5 rounded uppercase tracking-wider leading-none">Lig Ort.</span>}
                                        </div>
                                        <div>{renderNrfiStat(awayTrends.season_nrfi_pct, awayTrends.season_record, isFallback)}</div>
                                        <div>{renderNrfiStat(awayTrends.location_nrfi_pct, awayTrends.location_record, isFallback)}</div>
                                        <div className="flex justify-center items-center gap-1">
                                            {renderNrfiStat(awayTrends.last10_nrfi_pct, awayTrends.last10_record, isFallback)}
                                            {!isFallback && awayTrends.streak_emoji && <span className="text-xs">{awayTrends.streak_emoji}</span>}
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-[1.8fr_1fr_1fr_1fr] gap-2 text-center items-center">
                                        <div className="text-left text-[9px] md:text-[10px] font-bold text-gray-300 truncate pr-1 flex flex-col gap-0.5">
                                            {matchup.home_pitcher}
                                            {homePitcherNoData && <span className="text-[7px] font-black text-amber-500/80 bg-amber-500/10 border border-amber-500/20 px-1 py-0.5 rounded uppercase tracking-wider leading-none">Lig Ort.</span>}
                                        </div>
                                        <div>{renderNrfiStat(homeTrends.season_nrfi_pct, homeTrends.season_record, isFallback)}</div>
                                        <div>{renderNrfiStat(homeTrends.location_nrfi_pct, homeTrends.location_record, isFallback)}</div>
                                        <div className="flex justify-center items-center gap-1">
                                            {renderNrfiStat(homeTrends.last10_nrfi_pct, homeTrends.last10_record, isFallback)}
                                            {!isFallback && homeTrends.streak_emoji && <span className="text-xs">{homeTrends.streak_emoji}</span>}
                                        </div>
                                    </div>
                                </div>

                                <h3 className="text-[10px] text-gray-400 font-bold uppercase tracking-widest border-b border-slate-700 pb-1 mt-2 flex items-center gap-2">
                                    Team Offense NRFI Trends
                                    {isFallback && (
                                        <span className="text-[7px] font-black text-amber-500 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded uppercase tracking-wider">⚠️ No Trend Data</span>
                                    )}
                                </h3>
                                <div className="bg-slate-800/50 rounded-lg p-2 border border-slate-700/50">
                                    <div className="grid grid-cols-[1.8fr_1fr_1fr_1fr] gap-2 text-center items-center mb-2">
                                        <div className="text-left text-[8px] md:text-[9px] font-black text-slate-400 uppercase">Team</div>
                                        <div className="text-[8px] md:text-[9px] font-black text-slate-400 uppercase">Season</div>
                                        <div className="text-[8px] md:text-[9px] font-black text-slate-400 uppercase">Loc</div>
                                        <div className="text-[8px] md:text-[9px] font-black text-slate-400 uppercase">L10</div>
                                    </div>
                                    <div className="grid grid-cols-[1.8fr_1fr_1fr_1fr] gap-2 text-center items-center mb-2 border-b border-slate-700/30 pb-2">
                                        <div className="text-left text-[9px] md:text-[10px] font-bold text-gray-300 truncate pr-1">
                                            <span className="hidden xs:inline">{matchup.away_team}</span>
                                            <span className="xs:hidden">{getTeamAbbr(matchup.away_team)}</span>
                                        </div>
                                        <div>{renderNrfiStat(awayTeamNrfi.season_nrfi_pct, awayTeamNrfi.season_record, isFallback)}</div>
                                        <div>{renderNrfiStat(awayTeamNrfi.location_nrfi_pct, awayTeamNrfi.location_record, isFallback)}</div>
                                        <div>{renderNrfiStat(awayTeamNrfi.last10_nrfi_pct, awayTeamNrfi.last10_record, isFallback)}</div>
                                    </div>
                                    <div className="grid grid-cols-[1.8fr_1fr_1fr_1fr] gap-2 text-center items-center">
                                        <div className="text-left text-[9px] md:text-[10px] font-bold text-gray-300 truncate pr-1">
                                            <span className="hidden xs:inline">{matchup.home_team}</span>
                                            <span className="xs:hidden">{getTeamAbbr(matchup.home_team)}</span>
                                        </div>
                                        <div>{renderNrfiStat(homeTeamNrfi.season_nrfi_pct, homeTeamNrfi.season_record, isFallback)}</div>
                                        <div>{renderNrfiStat(homeTeamNrfi.location_nrfi_pct, homeTeamNrfi.location_record, isFallback)}</div>
                                        <div>{renderNrfiStat(homeTeamNrfi.last10_nrfi_pct, homeTeamNrfi.last10_record, isFallback)}</div>
                                    </div>
                                </div>
                            </div>

                            {/* RIGHT: AI Insight & Weather */}
                            <div className="flex flex-col gap-3">
                                <h3 className="text-[10px] text-gray-400 font-bold uppercase tracking-widest border-b border-slate-700 pb-1 flex items-center justify-between">
                                    AI Edge Insight
                                    {Weather?.cbs_alert_word && Weather?.cbs_alert_word !== "None" && (
                                        <span className={`px-1.5 py-0.5 rounded text-[8px] font-black tracking-wider ${Weather?.red_flag_alert ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'}`}>
                                            {Weather.cbs_alert_word}
                                        </span>
                                    )}
                                </h3>
                                <div className="bg-slate-800/40 rounded-lg p-3 border border-slate-700/50 flex-grow shadow-inner flex flex-col justify-start">
                                    <p className="text-[11px] md:text-xs text-gray-300 leading-relaxed font-semibold whitespace-pre-wrap">
                                        {formatAiInsight(aiInsight)}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default NrfiRow;