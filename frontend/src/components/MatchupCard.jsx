import React, { useState } from 'react';
import { formatAmericanOdds, getTeamLogo } from '../utils/formatters';

const getWeatherIcon = (condition) => {
    if (!condition) return '🏟️';
    const lowerCondition = condition.toLowerCase();
    if (lowerCondition.includes('rain') || lowerCondition.includes('drizzle')) return '🌧️';
    if (lowerCondition.includes('snow')) return '❄️';
    if (lowerCondition.includes('cloud') || lowerCondition.includes('overcast')) return '☁️';
    if (lowerCondition.includes('clear') || lowerCondition.includes('sun')) return '☀️';
    if (lowerCondition.includes('dome') || lowerCondition.includes('roof closed')) return '🏟️';
    return '⛅';
};

const MatchupCard = ({ prediction }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const { matchup, NRFI, F5, Full_Game, Details, Odds, Weather } = prediction;
    const pitcherAway = Details?.pitcher_analysis?.away || {};
    const pitcherHome = Details?.pitcher_analysis?.home || {};
    const isLive = matchup.status === "In Progress";

    return (
        <div className="bg-mlb-card rounded-xl border border-gray-700 shadow-2xl overflow-hidden mb-6 transition-all duration-300 hover:border-gray-500 w-full">

            {/* 1. ÜST BAR */}
            <div className="bg-slate-800/90 px-4 py-2.5 flex justify-between items-center text-[10px] md:text-xs text-gray-400 font-bold uppercase tracking-wider">
                <span className="truncate pr-2">{matchup.away_team} @ {matchup.home_team}</span>

                {isLive && (
                    <span className="text-green-400 font-black flex items-center gap-1.5 animate-pulse mx-auto">
                        <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_#22c55e]"></span> LIVE
                    </span>
                )}

                <div className="flex items-center gap-2">
                    {Weather && (
                        <span className="flex items-center gap-1.5 text-gray-200 bg-slate-900/60 px-2.5 py-1 rounded-md border border-slate-700/50">
                            {getWeatherIcon(Weather.condition)} {Weather.temp_f}°F
                        </span>
                    )}
                    <span className="bg-blue-600/20 text-blue-400 border border-blue-500/30 px-2 py-1 rounded flex-shrink-0">MLB</span>
                </div>
            </div>

            {/* 2. ANA KART İÇERİĞİ */}
            <div className="p-4 md:p-6">
                <div className="flex flex-wrap md:flex-nowrap items-start md:items-center justify-between relative w-full">

                    {/* SOL KOLON: DEPLASMAN TAKIMI */}
                    <div className="flex flex-col items-center w-1/2 md:w-1/3 order-1 text-center px-1">
                        <img src={getTeamLogo(matchup.away_team)} alt={matchup.away_team} className="w-16 h-16 md:w-20 md:h-20 mb-2 drop-shadow-lg" />

                        <div className="min-h-[44px] md:min-h-[56px] flex items-center justify-center w-full px-1 mb-1">
                            <h2 className="text-[15px] sm:text-lg md:text-xl font-black leading-tight balance-text">
                                {matchup.away_team}
                            </h2>
                        </div>

                        {/* Atıcı Kutusu Üste Çıktı */}
                        <div className="bg-slate-800/80 border border-slate-700 rounded-lg px-2 py-2 w-full max-w-[140px] shadow-inner mb-1.5">
                            <p className="text-xs text-gray-200 truncate font-bold">{matchup.away_pitcher}</p>
                            <p className="text-[10px] text-gray-400 mt-0.5">{pitcherAway.record} | {pitcherAway.era} ERA</p>
                        </div>

                        {/* Takım Formu (Genel Rekor ve Son 10 Maç) */}
                        <span className="text-[11px] text-gray-400 font-semibold tracking-wider">
                            {matchup.away_stats?.record} <span className="text-gray-600 mx-1">|</span> <span className="text-gray-500">L10: {matchup.away_stats?.l10}</span>
                        </span>
                    </div>

                    {/* SAĞ KOLON: EV SAHİBİ TAKIMI */}
                    <div className="flex flex-col items-center w-1/2 md:w-1/3 order-2 md:order-3 text-center px-1">
                        <img src={getTeamLogo(matchup.home_team)} alt={matchup.home_team} className="w-16 h-16 md:w-20 md:h-20 mb-2 drop-shadow-lg" />

                        <div className="min-h-[44px] md:min-h-[56px] flex items-center justify-center w-full px-1 mb-1">
                            <h2 className="text-[15px] sm:text-lg md:text-xl font-black leading-tight balance-text">
                                {matchup.home_team}
                            </h2>
                        </div>

                        {/* Atıcı Kutusu Üste Çıktı */}
                        <div className="bg-slate-800/80 border border-slate-700 rounded-lg px-2 py-2 w-full max-w-[140px] shadow-inner mb-1.5">
                            <p className="text-xs text-gray-200 truncate font-bold">{matchup.home_pitcher}</p>
                            <p className="text-[10px] text-gray-400 mt-0.5">{pitcherHome.record} | {pitcherHome.era} ERA</p>
                        </div>

                        {/* Takım Formu (Genel Rekor ve Son 10 Maç) */}
                        <span className="text-[11px] text-gray-400 font-semibold tracking-wider">
                            {matchup.home_stats?.record} <span className="text-gray-600 mx-1">|</span> <span className="text-gray-500">L10: {matchup.home_stats?.l10}</span>
                        </span>
                    </div>

                    {/* ORTA KOLON: Skor, Saat, Oranlar */}
                    <div className="flex flex-col items-center justify-center w-full md:w-1/3 order-3 md:order-2 mt-6 md:mt-0 pt-5 md:pt-0 border-t border-slate-700/50 md:border-0 relative z-10">

                        <div className="text-center mb-3">
                            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">{matchup.game_time || "TBD"}</span>
                        </div>

                        <div className="text-center mb-4">
                            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest block mb-1.5">Proj. Score</span>
                            <div className="text-3xl md:text-4xl font-black text-white bg-slate-900/60 px-6 py-2 rounded-xl border border-slate-700 shadow-inner tracking-tight">
                                {Full_Game.full_away_score} <span className="text-gray-600 font-medium mx-1">-</span> {Full_Game.full_home_score}
                            </div>
                        </div>

                        <div className="flex items-center justify-center gap-3 mb-5 w-full max-w-[280px]">
                            <div className="text-xs font-black text-gray-400 w-9 text-right">{Math.round(Full_Game.full_away_win_prob * 100)}%</div>
                            <div className="flex-grow h-2 bg-slate-800 rounded-full overflow-hidden flex border border-slate-700/50">
                                <div style={{ width: `${Full_Game.full_away_win_prob * 100}%` }} className="bg-blue-500 h-full"></div>
                                <div style={{ width: `${Full_Game.full_home_win_prob * 100}%` }} className="bg-red-500 h-full"></div>
                            </div>
                            <div className="text-xs font-black text-gray-400 w-9 text-left">{Math.round(Full_Game.full_home_win_prob * 100)}%</div>
                        </div>

                        {/* ML ODDS */}
                        <div className="bg-slate-900/60 border border-slate-700 rounded-xl px-4 pt-3.5 pb-2.5 w-full max-w-[260px] flex items-center justify-between relative shadow-lg">
                            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-slate-800 border border-slate-600 px-3 py-0.5 rounded-full text-[10px] md:text-xs font-black text-gray-300 shadow-md whitespace-nowrap">
                                Book O/U: {Odds.over_under}
                            </div>

                            <div className="flex flex-col items-center w-2/5">
                                <span className={`text-lg md:text-xl font-black tracking-tight ${Odds.away_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-200'}`}>
                                    {formatAmericanOdds(Odds.best_away_odds)}
                                </span>
                            </div>
                            <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest w-1/5 text-center">ML</div>
                            <div className="flex flex-col items-center w-2/5">
                                <span className={`text-lg md:text-xl font-black tracking-tight ${Odds.home_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-200'}`}>
                                    {formatAmericanOdds(Odds.best_home_odds)}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* ALT BİLGİ VE BUTONLAR */}
                <div className="mt-6 md:mt-8 pt-4 border-t border-slate-700/80 flex flex-wrap justify-between items-center gap-4">
                    <div className="flex items-center gap-3">
                        {Details?.value_alerts?.length > 0 && (
                            <span className="animate-pulse bg-green-900/20 border border-mlb-green/40 px-3 py-1.5 rounded-md text-mlb-green text-xs font-black uppercase flex items-center shadow-[0_0_10px_rgba(34,197,94,0.1)]">
                                🔥 Edge Alert
                            </span>
                        )}
                    </div>

                    <div className="flex items-center gap-4 ml-auto">
                        <span className="text-gray-400 text-xs font-bold uppercase tracking-wider cursor-pointer hover:text-white transition-colors">
                            Matchup 📊
                        </span>
                        <button
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="text-xs bg-blue-600/90 hover:bg-blue-500 text-white px-5 py-2 rounded-lg transition-colors font-black uppercase tracking-wider shadow-lg"
                        >
                            {isExpanded ? 'Hide Details ⬆' : 'Details ⬇'}
                        </button>
                    </div>
                </div>
            </div>

            {/* 3. EXPAND ALANI */}
            <div className={`bg-slate-900 border-t border-slate-700 overflow-hidden transition-all duration-500 ease-in-out ${isExpanded ? 'max-h-[1500px] opacity-100 p-4 md:p-6' : 'max-h-0 opacity-0 p-0'}`}>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">

                    {/* NRFI/YRFI Card */}
                    <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/80">
                        <div className="flex justify-between items-start mb-5">
                            <div>
                                <h3 className={`text-2xl font-black ${NRFI.pick === 'NRFI' ? 'text-blue-400' : 'text-red-400'}`}>
                                    {Math.round(NRFI.confidence * 100)}%
                                </h3>
                                <p className={`text-[10px] font-black uppercase tracking-widest ${NRFI.pick === 'NRFI' ? 'text-blue-500/80' : 'text-red-500/80'}`}>
                                    {NRFI.pick} Probability
                                </p>
                            </div>
                        </div>

                        <div className="flex justify-between items-center text-center">
                            <div className="w-1/3 flex flex-col items-center">
                                <img src={getTeamLogo(matchup.away_team)} alt="Away" className="w-10 h-10 opacity-80 mb-2 drop-shadow-md" />
                                <div className="bg-slate-900 px-3 py-1 rounded-md text-xs font-black text-gray-300 border border-slate-700 mb-2 w-full">
                                    {pitcherAway.fip} FIP
                                </div>
                                <div className="bg-slate-900 px-3 py-1 rounded-md text-xs font-black text-gray-300 border border-slate-700 w-full">
                                    {Math.round(pitcherAway.k_bb_pct * 100)}% K-BB
                                </div>
                            </div>

                            <div className="w-1/3 text-[10px] text-gray-500 font-bold uppercase tracking-widest flex flex-col gap-6">
                                <span>Pitcher Skills</span>
                                <span>Edge</span>
                            </div>

                            <div className="w-1/3 flex flex-col items-center">
                                <img src={getTeamLogo(matchup.home_team)} alt="Home" className="w-10 h-10 opacity-80 mb-2 drop-shadow-md" />
                                <div className="bg-slate-900 px-3 py-1 rounded-md text-xs font-black text-gray-300 border border-slate-700 mb-2 w-full">
                                    {pitcherHome.fip} FIP
                                </div>
                                <div className="bg-slate-900 px-3 py-1 rounded-md text-xs font-black text-gray-300 border border-slate-700 w-full">
                                    {Math.round(pitcherHome.k_bb_pct * 100)}% K-BB
                                </div>
                            </div>
                        </div>

                        <div className="mt-5 pt-3 border-t border-slate-700/50 text-center bg-slate-900/30 rounded-b-lg -mx-5 -mb-5 pb-3">
                            <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Model Outcome: <span className={`text-sm font-black ${NRFI.pick === 'NRFI' ? 'text-blue-400' : 'text-red-400'}`}>{NRFI.pick}</span></span>
                        </div>
                    </div>

                    {/* F5 & Totals Card */}
                    <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/80 flex flex-col justify-between">
                        <div>
                            <h3 className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-4 border-b border-slate-700 pb-2">F5 & Totals Projection</h3>
                            <div className="flex justify-between text-sm mb-4 items-center">
                                <span className="text-gray-400 font-semibold">F5 Score:</span>
                                <span className="font-black text-white bg-slate-900 px-4 py-1.5 rounded-lg border border-slate-700 text-lg">
                                    {F5.f5_away_score} - {F5.f5_home_score}
                                </span>
                            </div>
                            <div className="flex justify-between text-sm mb-4 items-center">
                                <span className="text-gray-400 font-semibold">Model O/U Total:</span>
                                <span className="font-black text-white bg-slate-900 px-4 py-1.5 rounded-lg border border-slate-700">
                                    {Full_Game.full_total} runs
                                </span>
                            </div>
                        </div>
                        <div className="flex justify-between text-sm items-center bg-slate-900/50 p-3 rounded-lg border border-slate-700/50 mt-auto">
                            <span className="text-gray-400 font-semibold">Total Diff:</span>
                            <span className={`font-black text-sm ${Full_Game.full_total > Odds.over_under ? 'text-mlb-green' : 'text-blue-400'}`}>
                                {Math.abs(Full_Game.full_total - Odds.over_under).toFixed(1)} {Full_Game.full_total > Odds.over_under ? 'OVER' : 'UNDER'} Book
                            </span>
                        </div>
                    </div>

                    {/* Ballpark Context */}
                    <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/80 md:col-span-2 flex flex-col md:flex-row items-center justify-between overflow-hidden relative">
                        <div className="relative z-10 w-full md:w-auto text-center md:text-left">
                            <h3 className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-3">Ballpark Context</h3>
                            {Weather ? (
                                <>
                                    <div className="text-2xl md:text-3xl font-black text-white flex justify-center md:justify-start items-center gap-3 mb-2">
                                        {getWeatherIcon(Weather.condition)} {Weather.temp_f}°F
                                    </div>
                                    <div className="text-sm font-medium text-gray-300 bg-slate-900/60 px-3 py-1.5 rounded-md inline-block">
                                        <span className="text-gray-500 mr-2">WIND</span> {Weather.wind_mph} mph ({Weather.wind_direction})
                                    </div>
                                    <div className="text-sm font-medium text-gray-300 mt-2">
                                        {Weather.condition}
                                    </div>
                                    <div className="text-sm font-medium text-gray-300 mt-1">
                                        <span className="text-gray-500 mr-2">HUMIDITY</span> {Weather.humidity}%
                                    </div>
                                </>
                            ) : (
                                <span className="text-sm text-gray-500">Weather data unavailable</span>
                            )}
                        </div>

                        <div className="text-7xl opacity-[0.03] absolute right-4 top-1/2 -translate-y-1/2 md:relative md:opacity-10 md:transform-none mt-4 md:mt-0">
                            {Weather?.wind_mph > 10 ? '💨' : '🏟️'}
                        </div>
                    </div>

                </div>
            </div>

        </div>
    );
};

export default MatchupCard;