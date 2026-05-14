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
        <div className="bg-mlb-card rounded-xl border border-gray-700 shadow-2xl overflow-hidden mb-8 transition-all duration-300 hover:border-gray-500 w-full">

            {/* ================= 1. ÜST BAR (Mobilde Daralma Düzeltildi) ================= */}
            <div className="bg-slate-800/90 px-3 py-2 flex justify-between items-center border-b border-gray-700/50 gap-2">
                <div className="flex items-center gap-1.5 flex-1 min-w-0">
                    <span className="bg-blue-600/20 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded text-[9px] font-black tracking-widest flex-shrink-0">MLB</span>
                    <span className="text-[9px] md:text-xs text-gray-300 font-bold uppercase tracking-wider truncate">
                        {matchup.away_team} @ {matchup.home_team}
                    </span>
                </div>

                {isLive && (
                    <span className="text-green-400 text-[10px] md:text-xs font-black flex items-center gap-1 animate-pulse flex-shrink-0">
                        <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_#22c55e]"></span> LIVE
                    </span>
                )}

                <div className="flex items-center gap-2 flex-shrink-0">
                    {Weather && (
                        <span className="flex items-center gap-1 text-gray-300 bg-slate-900/60 px-2 py-1 rounded border border-slate-700/50 text-[9px] md:text-[10px] font-bold whitespace-nowrap">
                            {getWeatherIcon(Weather.condition)} {Weather.temp_f}°F
                        </span>
                    )}
                </div>
            </div>

            {/* ================= 2. ANA KART İÇERİĞİ ================= */}
            <div className="p-3 md:p-6">

                {/* LOGOLAR, SAAT VE ATICILAR (Flex-1 ve Whitespace-nowrap Düzeltmesi) */}
                <div className="flex w-full justify-between items-start mb-5">

                    {/* DEPLASMAN */}
                    <div className="flex-1 flex flex-col items-center text-center w-0 px-1">
                        <img src={getTeamLogo(matchup.away_team)} alt={matchup.away_team} className="w-14 h-14 md:w-20 md:h-20 mb-2 drop-shadow-lg" />
                        <div className="min-h-[40px] md:min-h-[48px] flex items-center justify-center w-full mb-2">
                            <h2 className="text-[13px] md:text-lg font-black leading-tight balance-text">{matchup.away_team}</h2>
                        </div>
                        <div className="bg-slate-800/80 border border-slate-700 rounded-lg px-1.5 md:px-2 py-1.5 w-full max-w-[120px] md:max-w-[140px] shadow-inner mx-auto">
                            <p className="text-[11px] md:text-xs text-gray-200 truncate font-bold">{matchup.away_pitcher}</p>
                            <p className="text-[9px] md:text-[10px] text-gray-400 truncate">{pitcherAway.record} | {pitcherAway.era} ERA</p>
                        </div>
                    </div>

                    {/* ORTA: SAAT (Asla Alt Satıra Geçmez) */}
                    <div className="flex-shrink-0 flex flex-col items-center justify-start pt-2 px-1">
                        <span className="text-[8px] md:text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1 text-center">Game Time</span>
                        <span className="text-[10px] md:text-sm font-black text-gray-300 bg-slate-900/50 px-2.5 py-1 rounded-full border border-slate-700/50 whitespace-nowrap">
                            {matchup.game_time || "TBD"}
                        </span>
                    </div>

                    {/* EV SAHİBİ */}
                    <div className="flex-1 flex flex-col items-center text-center w-0 px-1">
                        <img src={getTeamLogo(matchup.home_team)} alt={matchup.home_team} className="w-14 h-14 md:w-20 md:h-20 mb-2 drop-shadow-lg" />
                        <div className="min-h-[40px] md:min-h-[48px] flex items-center justify-center w-full mb-2">
                            <h2 className="text-[13px] md:text-lg font-black leading-tight balance-text">{matchup.home_team}</h2>
                        </div>
                        <div className="bg-slate-800/80 border border-slate-700 rounded-lg px-1.5 md:px-2 py-1.5 w-full max-w-[120px] md:max-w-[140px] shadow-inner mx-auto">
                            <p className="text-[11px] md:text-xs text-gray-200 truncate font-bold">{matchup.home_pitcher}</p>
                            <p className="text-[9px] md:text-[10px] text-gray-400 truncate">{pitcherHome.record} | {pitcherHome.era} ERA</p>
                        </div>
                    </div>
                </div>

                {/* COVERS STİLİ STACKED KAYITLAR */}
                <div className="flex justify-center items-center w-full mb-6 bg-slate-900/40 rounded-lg py-3 border border-slate-700/50 max-w-[320px] mx-auto shadow-inner px-2">
                    <div className="flex flex-col flex-1 text-right pr-3 md:pr-4 gap-2">
                        <span className="text-[10px] md:text-[11px] font-black text-gray-300">{matchup.away_stats?.record}</span>
                        <span className="text-[10px] md:text-[11px] font-black text-gray-400">{matchup.away_stats?.l10}</span>
                    </div>
                    <div className="flex flex-col flex-shrink-0 text-center gap-2 border-x border-slate-700/50 px-3 md:px-4">
                        <span className="text-[8px] md:text-[9px] text-gray-500 font-black uppercase tracking-widest">W / L</span>
                        <span className="text-[8px] md:text-[9px] text-gray-500 font-black uppercase tracking-widest">L 10</span>
                    </div>
                    <div className="flex flex-col flex-1 text-left pl-3 md:pl-4 gap-2">
                        <span className="text-[10px] md:text-[11px] font-black text-gray-300">{matchup.home_stats?.record}</span>
                        <span className="text-[10px] md:text-[11px] font-black text-gray-400">{matchup.home_stats?.l10}</span>
                    </div>
                </div>

                {/* SKOR TAHMİNİ, WIN PROB VE ORANLAR */}
                <div className="flex flex-col items-center justify-center w-full border-t border-slate-700/50 pt-5 relative z-10">

                    {/* Proj Score */}
                    <div className="text-center mb-4">
                        <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest block mb-1.5">Proj. Score</span>
                        <div className="text-3xl md:text-4xl font-black text-white bg-slate-900/80 px-8 py-2 rounded-xl border border-slate-700 shadow-[0_0_15px_rgba(0,0,0,0.5)] tracking-tight">
                            {Full_Game.full_away_score} <span className="text-gray-600 font-medium mx-2">-</span> {Full_Game.full_home_score}
                        </div>
                    </div>

                    {/* Win Prob Bar */}
                    <div className="flex items-center justify-center gap-3 mb-5 w-full max-w-[280px]">
                        <div className="text-[11px] font-black text-gray-400 w-8 text-right">{Math.round(Full_Game.full_away_win_prob * 100)}%</div>
                        <div className="flex-grow h-1.5 bg-slate-800 rounded-full overflow-hidden flex border border-slate-700/50">
                            <div style={{ width: `${Full_Game.full_away_win_prob * 100}%` }} className="bg-blue-500 h-full"></div>
                            <div style={{ width: `${Full_Game.full_home_win_prob * 100}%` }} className="bg-red-500 h-full"></div>
                        </div>
                        <div className="text-[11px] font-black text-gray-400 w-8 text-left">{Math.round(Full_Game.full_home_win_prob * 100)}%</div>
                    </div>

                    {/* ML Odds & Book O/U */}
                    <div className="bg-slate-900/80 border border-slate-700 rounded-xl px-5 pt-4 pb-3 w-full max-w-[280px] flex items-center justify-between relative shadow-lg">
                        <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-slate-800 border border-slate-600 px-4 py-0.5 rounded-full text-[10px] font-black text-gray-300 shadow-md whitespace-nowrap">
                            Book O/U: {Odds.over_under}
                        </div>

                        <div className="flex flex-col items-center w-2/5">
                            <span className={`text-xl font-black tracking-tight ${Odds.away_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-200'}`}>
                                {formatAmericanOdds(Odds.best_away_odds)}
                            </span>
                        </div>
                        <div className="text-[10px] font-bold text-gray-600 uppercase tracking-widest w-1/5 text-center">ML</div>
                        <div className="flex flex-col items-center w-2/5">
                            <span className={`text-xl font-black tracking-tight ${Odds.home_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-200'}`}>
                                {formatAmericanOdds(Odds.best_home_odds)}
                            </span>
                        </div>
                    </div>
                </div>

                {/* ================= ALT BİLGİ VE BUTONLAR ================= */}
                <div className="mt-8 pt-4 border-t border-slate-700/80 flex flex-wrap justify-between items-center gap-4">
                    <div className="flex items-center gap-2">
                        {Details?.value_alerts?.length > 0 && (
                            <span className="animate-pulse bg-green-900/20 border border-mlb-green/40 px-2.5 py-1.5 rounded-md text-mlb-green text-[9px] md:text-[10px] font-black uppercase flex items-center shadow-[0_0_10px_rgba(34,197,94,0.1)]">
                                🔥 Edge Alert
                            </span>
                        )}
                    </div>

                    <div className="flex items-center gap-3 md:gap-4 ml-auto">
                        <span className="text-gray-400 text-[10px] md:text-xs font-bold uppercase tracking-wider">
                            Matchup 📊
                        </span>
                        <button
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="text-[10px] md:text-[11px] bg-blue-600/90 hover:bg-blue-500 text-white px-4 md:px-5 py-2 md:py-2.5 rounded-lg transition-colors font-black uppercase tracking-wider shadow-lg"
                        >
                            {isExpanded ? 'Hide Details ⬆' : 'Details ⬇'}
                        </button>
                    </div>
                </div>
            </div>

            {/* ================= 3. EXPAND ALANI (IN-DEPTH) ================= */}
            <div className={`bg-slate-900 border-t border-slate-700 overflow-hidden transition-all duration-500 ease-in-out ${isExpanded ? 'max-h-[1500px] opacity-100 p-4 md:p-6' : 'max-h-0 opacity-0 p-0'}`}>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">

                    {/* YENİ NRFI/YRFI KARTI (IMG_3226 MİMİC) */}
                    <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/80 flex flex-col justify-between">
                        <div className="mb-4 text-center md:text-left">
                            <h3 className={`text-3xl font-black tracking-tighter ${NRFI.pick === 'NRFI' ? 'text-mlb-green' : 'text-red-400'}`}>
                                {Math.round(NRFI.confidence * 100)}%
                            </h3>
                            <p className={`text-[10px] font-black uppercase tracking-widest ${NRFI.pick === 'NRFI' ? 'text-mlb-green/80' : 'text-red-500/80'}`}>
                                {NRFI.pick} Probability
                            </p>
                        </div>

                        {/* Etiketler Ortada, Değerler Kenarlarda (Covers/IMG_3226 Style) */}
                        <div className="flex justify-center items-center w-full bg-slate-900/50 rounded-lg py-3 border border-slate-700/50 my-2">
                            <div className="flex flex-col w-[35%] items-center gap-2">
                                <span className="bg-slate-800 px-3 py-1 rounded-full text-[10px] font-black text-gray-300 border border-slate-700">{pitcherAway.fip}</span>
                                <span className="bg-slate-800 px-3 py-1 rounded-full text-[10px] font-black text-gray-300 border border-slate-700">{Math.round(pitcherAway.k_bb_pct * 100)}%</span>
                            </div>
                            <div className="flex flex-col w-[30%] text-center gap-3">
                                <span className="text-[9px] text-gray-500 font-black uppercase tracking-widest leading-tight">Pitcher<br />FIP</span>
                                <span className="text-[9px] text-gray-500 font-black uppercase tracking-widest leading-tight">K-BB<br />Strike%</span>
                            </div>
                            <div className="flex flex-col w-[35%] items-center gap-2">
                                <span className="bg-slate-800 px-3 py-1 rounded-full text-[10px] font-black text-gray-300 border border-slate-700">{pitcherHome.fip}</span>
                                <span className="bg-slate-800 px-3 py-1 rounded-full text-[10px] font-black text-gray-300 border border-slate-700">{Math.round(pitcherHome.k_bb_pct * 100)}%</span>
                            </div>
                        </div>

                        <div className="mt-4 pt-3 border-t border-slate-700/50 text-center">
                            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Model Outcome: <span className={`text-sm font-black italic ml-1 ${NRFI.pick === 'NRFI' ? 'text-blue-400' : 'text-red-400'}`}>{NRFI.pick}</span></span>
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

                    {/* Ballpark Context (Weather & Humidity) */}
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