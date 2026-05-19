import React, { useState } from 'react';
import { getTeamLogo } from '../utils/formatters';

const getNrfiColor = (pct) => {
    if (pct === 'N/A' || !pct) return 'bg-slate-800 text-gray-500 border-slate-700';
    if (pct >= 70) return 'bg-red-500/20 text-red-400 border-red-500/30'; // Hot
    if (pct <= 40) return 'bg-blue-500/20 text-blue-400 border-blue-500/30'; // Cold
    return 'bg-slate-700 text-gray-300 border-slate-600'; // Neutral
};

const renderNrfiStat = (pct, record) => {
    if (pct === 'N/A' || !pct) return <span className="text-gray-600 font-bold text-xs">-</span>;
    return (
        <div className="flex flex-col items-center justify-center">
            <span className={`px-1.5 py-0.5 rounded text-[10px] md:text-xs font-black border tracking-wider shadow-sm ${getNrfiColor(pct)}`}>
                {pct}%
            </span>
            {record && record !== "0-0" && <span className="text-[8px] md:text-[9px] text-gray-400 font-bold mt-1 tracking-wider whitespace-nowrap">{record}</span>}
        </div>
    );
};

const NrfiRow = ({ prediction }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    
    const { matchup, NRFI, Details, Weather } = prediction;
    const trends = NRFI?.scraped_trends || {};
    const awayTrends = trends?.away_pitcher || {};
    const homeTrends = trends?.home_pitcher || {};
    const awayTeamNrfi = trends?.away_team_nrfi || {};
    const homeTeamNrfi = trends?.home_team_nrfi || {};
    const aiInsight = Details?.ai_insight;

    // AI/Algo Score
    const nrfiScore = (NRFI?.nrfi_score * 100).toFixed(1);
    const yrfiScore = (NRFI?.yrfi_score * 100).toFixed(1);
    const pick = NRFI?.pick;
    
    const isNrfiFavored = NRFI?.nrfi_score >= NRFI?.yrfi_score;
    const scoreColor = isNrfiFavored ? "text-green-400 bg-green-500/10 border-green-500/30" : "text-red-400 bg-red-500/10 border-red-500/30";

    return (
        <div className="bg-mlb-card rounded-xl border border-gray-700 shadow-lg overflow-hidden mb-3 transition-all duration-300 hover:border-gray-500 w-full">
            {/* Header / Summary Row */}
            <div className="p-3 md:p-4 flex flex-col md:flex-row items-center justify-between gap-4">
                
                {/* Team Matchup & Logos */}
                <div className="flex items-center gap-4 w-full md:w-auto flex-1 justify-between md:justify-start">
                    <div className="flex items-center gap-2">
                        <img src={getTeamLogo(matchup.away_team)} alt={matchup.away_team} className="w-8 h-8 md:w-10 md:h-10 drop-shadow-md" />
                        <span className="text-xs md:text-sm font-black text-white w-12 md:w-auto truncate">{matchup.away_team}</span>
                    </div>
                    <span className="text-[10px] md:text-xs font-black text-gray-500">@</span>
                    <div className="flex items-center gap-2">
                        <img src={getTeamLogo(matchup.home_team)} alt={matchup.home_team} className="w-8 h-8 md:w-10 md:h-10 drop-shadow-md" />
                        <span className="text-xs md:text-sm font-black text-white w-12 md:w-auto truncate">{matchup.home_team}</span>
                    </div>
                </div>

                {/* Algo Score & Game Time */}
                <div className="flex items-center justify-between w-full md:w-auto gap-4 md:gap-8">
                    <div className="flex flex-col items-center">
                        <span className="text-[8px] md:text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">AI Score</span>
                        <div className={`px-2 py-1 rounded border font-black text-xs md:text-sm ${scoreColor}`}>
                            {pick} {isNrfiFavored ? nrfiScore : yrfiScore}%
                        </div>
                    </div>
                    <div className="flex flex-col items-center">
                        <span className="text-[8px] md:text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">Time</span>
                        <span className="text-[10px] md:text-xs font-black text-gray-300 whitespace-nowrap">{matchup.game_time || "TBD"}</span>
                    </div>

                    {/* Expand Details Button */}
                    <button 
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-[10px] md:text-xs font-bold transition-colors ml-auto md:ml-0"
                    >
                        {isExpanded ? "Hide" : "Details"}
                        <svg className={`w-3 h-3 transition-transform ${isExpanded ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M19 9l-7 7-7-7"></path></svg>
                    </button>
                </div>
            </div>

            {/* Dropdown Detail View */}
            {isExpanded && (
                <div className="border-t border-gray-700/50 bg-slate-900/40 p-3 md:p-4 animate-in fade-in slide-in-from-top-2 duration-200">
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* LEFT: Pitcher & Team NRFI Records */}
                        <div className="flex flex-col gap-3">
                            <h3 className="text-[10px] text-gray-400 font-bold uppercase tracking-widest border-b border-slate-700 pb-1">Pitcher NRFI Trends</h3>
                            <div className="bg-slate-800/50 rounded-lg p-2 border border-slate-700/50">
                                <div className="grid grid-cols-4 gap-2 text-center items-center mb-2">
                                    <div className="text-left text-[8px] md:text-[9px] font-black text-gray-500 uppercase">Pitcher</div>
                                    <div className="text-[8px] md:text-[9px] font-black text-gray-500 uppercase">Season</div>
                                    <div className="text-[8px] md:text-[9px] font-black text-gray-500 uppercase">Loc</div>
                                    <div className="text-[8px] md:text-[9px] font-black text-gray-500 uppercase">L10</div>
                                </div>
                                <div className="grid grid-cols-4 gap-2 text-center items-center mb-2 border-b border-slate-700/30 pb-2">
                                    <div className="text-left text-[9px] md:text-[10px] font-bold text-gray-300 truncate pr-1">{matchup.away_pitcher}</div>
                                    <div>{renderNrfiStat(awayTrends.season_nrfi_pct, awayTrends.season_record)}</div>
                                    <div>{renderNrfiStat(awayTrends.location_nrfi_pct, awayTrends.location_record)}</div>
                                    <div className="flex justify-center items-center gap-1">
                                        {renderNrfiStat(awayTrends.last10_nrfi_pct, awayTrends.last10_record)}
                                        {awayTrends.streak_emoji && <span className="text-xs">{awayTrends.streak_emoji}</span>}
                                    </div>
                                </div>
                                <div className="grid grid-cols-4 gap-2 text-center items-center">
                                    <div className="text-left text-[9px] md:text-[10px] font-bold text-gray-300 truncate pr-1">{matchup.home_pitcher}</div>
                                    <div>{renderNrfiStat(homeTrends.season_nrfi_pct, homeTrends.season_record)}</div>
                                    <div>{renderNrfiStat(homeTrends.location_nrfi_pct, homeTrends.location_record)}</div>
                                    <div className="flex justify-center items-center gap-1">
                                        {renderNrfiStat(homeTrends.last10_nrfi_pct, homeTrends.last10_record)}
                                        {homeTrends.streak_emoji && <span className="text-xs">{homeTrends.streak_emoji}</span>}
                                    </div>
                                </div>
                            </div>

                            <h3 className="text-[10px] text-gray-400 font-bold uppercase tracking-widest border-b border-slate-700 pb-1 mt-2">Team Offense NRFI Trends</h3>
                            <div className="bg-slate-800/50 rounded-lg p-2 border border-slate-700/50">
                                <div className="grid grid-cols-4 gap-2 text-center items-center mb-2">
                                    <div className="text-left text-[8px] md:text-[9px] font-black text-gray-500 uppercase">Team</div>
                                    <div className="text-[8px] md:text-[9px] font-black text-gray-500 uppercase">Season</div>
                                    <div className="text-[8px] md:text-[9px] font-black text-gray-500 uppercase">Loc</div>
                                    <div className="text-[8px] md:text-[9px] font-black text-gray-500 uppercase">L10</div>
                                </div>
                                <div className="grid grid-cols-4 gap-2 text-center items-center mb-2 border-b border-slate-700/30 pb-2">
                                    <div className="text-left text-[9px] md:text-[10px] font-bold text-gray-300 truncate pr-1">{matchup.away_team}</div>
                                    <div>{renderNrfiStat(awayTeamNrfi.season_nrfi_pct, awayTeamNrfi.season_record)}</div>
                                    <div>{renderNrfiStat(awayTeamNrfi.location_nrfi_pct, awayTeamNrfi.location_record)}</div>
                                    <div>{renderNrfiStat(awayTeamNrfi.last10_nrfi_pct, awayTeamNrfi.last10_record)}</div>
                                </div>
                                <div className="grid grid-cols-4 gap-2 text-center items-center">
                                    <div className="text-left text-[9px] md:text-[10px] font-bold text-gray-300 truncate pr-1">{matchup.home_team}</div>
                                    <div>{renderNrfiStat(homeTeamNrfi.season_nrfi_pct, homeTeamNrfi.season_record)}</div>
                                    <div>{renderNrfiStat(homeTeamNrfi.location_nrfi_pct, homeTeamNrfi.location_record)}</div>
                                    <div>{renderNrfiStat(homeTeamNrfi.last10_nrfi_pct, homeTeamNrfi.last10_record)}</div>
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
                            <div className="bg-slate-800/40 rounded-lg p-3 border border-slate-700/50 flex-grow shadow-inner">
                                <p className="text-[11px] md:text-xs text-gray-300 leading-relaxed font-medium whitespace-pre-wrap">
                                    {aiInsight || "No AI insight available for this matchup."}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default NrfiRow;
