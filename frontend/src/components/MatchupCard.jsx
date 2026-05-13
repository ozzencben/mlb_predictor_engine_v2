import React, { useState } from 'react';
import { formatAmericanOdds, getTeamLogo } from '../utils/formatters';

// Hava durumu ikon fonksiyonu
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
    // Expand state
    const [isExpanded, setIsExpanded] = useState(false);

    const { matchup, NRFI, F5, Full_Game, Details, Odds, Weather } = prediction;
    const pitcherAway = Details?.pitcher_analysis?.away || {};
    const pitcherHome = Details?.pitcher_analysis?.home || {};

    // Maç "Live" mı kontrolü
    const isLive = matchup.status === "In Progress";

    return (
        <div className="bg-mlb-card rounded-xl border border-gray-700 shadow-2xl overflow-hidden mb-6 transition-all duration-300 hover:border-gray-500">

            {/* 1. ÜST BAR: Takımlar, Canlı Durumu ve Hava Durumu */}
            <div className="bg-slate-800/80 px-3 md:px-4 py-2 flex justify-between items-center text-[10px] md:text-xs text-gray-400 font-bold uppercase tracking-wider">
                <span className="truncate pr-2">{matchup.away_team} @ {matchup.home_team}</span>

                {/* Tyler'ın İstediği Live İbaresi */}
                {isLive && (
                    <span className="text-green-400 font-black flex items-center gap-1 animate-pulse">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span> Live
                    </span>
                )}

                <div className="flex items-center gap-3">
                    {Weather && (
                        <span className="flex items-center gap-1 text-gray-300 bg-slate-900/50 px-2 py-0.5 rounded">
                            {getWeatherIcon(Weather.condition)} {Weather.temp_f}°F
                        </span>
                    )}
                    <span className="bg-blue-600/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded flex-shrink-0">MLB</span>
                </div>
            </div>

            {/* 2. ANA KART İÇERİĞİ (Her Zaman Görünür) */}
            <div className="p-4 md:p-6">
                <div className="flex flex-wrap md:flex-nowrap items-start md:items-center justify-between relative">

                    {/* DEPLASMAN TAKIMI */}
                    <div className="flex flex-col items-center w-[45%] md:w-1/3 order-1 text-center">
                        <img src={getTeamLogo(matchup.away_team)} alt={matchup.away_team} className="w-14 h-14 md:w-20 md:h-20 mb-2 drop-shadow-lg" />
                        <h2 className="text-base md:text-xl font-black leading-tight">{matchup.away_team}</h2>
                        {/* Takım Kaydı logoların altında (Tyler'ın istediği yer) */}
                        <span className="text-xs text-gray-400 font-semibold mb-3">{matchup.away_stats?.record}</span>

                        <div className="bg-slate-800/80 border border-slate-700 rounded px-3 py-1.5 w-full max-w-[140px]">
                            <p className="text-xs text-gray-300 truncate font-bold">{matchup.away_pitcher}</p>
                            {/* Pitcher W-L ve ERA */}
                            <p className="text-[10px] text-gray-400">{pitcherAway.record} | {pitcherAway.era} ERA</p>
                        </div>
                    </div>

                    {/* ORTAYA TARİH/SAAT EKLENDİ (Tyler IMG_3764) */}
                    <div className="hidden md:flex flex-col items-center justify-center w-[10%] order-2 h-full absolute left-1/2 -translate-x-1/2 top-4">
                        <span className="text-xs text-gray-500 font-bold uppercase">Game Time</span>
                        <span className="text-sm font-black text-gray-300">{matchup.game_time || "TBD"}</span>
                    </div>

                    {/* EV SAHİBİ TAKIMI */}
                    <div className="flex flex-col items-center w-[45%] md:w-1/3 order-2 md:order-3 text-center">
                        <img src={getTeamLogo(matchup.home_team)} alt={matchup.home_team} className="w-14 h-14 md:w-20 md:h-20 mb-2 drop-shadow-lg" />
                        <h2 className="text-base md:text-xl font-black leading-tight">{matchup.home_team}</h2>
                        <span className="text-xs text-gray-400 font-semibold mb-3">{matchup.home_stats?.record}</span>

                        <div className="bg-slate-800/80 border border-slate-700 rounded px-3 py-1.5 w-full max-w-[140px]">
                            <p className="text-xs text-gray-300 truncate font-bold">{matchup.home_pitcher}</p>
                            <p className="text-[10px] text-gray-400">{pitcherHome.record} | {pitcherHome.era} ERA</p>
                        </div>
                    </div>

                    {/* MOBİL İÇİN TARİH/SAAT (Alt Satıra İner) */}
                    <div className="w-full text-center mt-4 order-3 md:hidden">
                        <span className="text-xs text-gray-400 font-bold">{matchup.game_time || "TBD"}</span>
                    </div>

                    {/* ORTA ALAN: Skor Tahmini ve ML Oranlar */}
                    <div className="flex flex-col items-center w-full md:w-1/3 order-4 md:order-2 mt-6 md:mt-0 pt-5 md:pt-0 border-t border-gray-700/50 md:border-0 relative z-10 md:mt-[100px]">

                        <div className="text-center mb-3">
                            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest block mb-1">Proj. Score</span>
                            <div className="text-3xl font-black text-white bg-slate-900/40 px-5 py-2 rounded-lg border border-slate-700">
                                {Full_Game.full_away_score} <span className="text-gray-600 font-normal mx-1">-</span> {Full_Game.full_home_score}
                            </div>
                        </div>

                        {/* WIN PROBABILITIES BAR */}
                        <div className="flex items-center gap-2 mb-4 w-full px-4">
                            <div className="text-xs font-black text-gray-400 w-8 text-right">{Math.round(Full_Game.full_away_win_prob * 100)}%</div>
                            <div className="flex-grow h-1.5 bg-gray-700 rounded-full overflow-hidden flex">
                                <div style={{ width: `${Full_Game.full_away_win_prob * 100}%` }} className="bg-blue-500 h-full"></div>
                                <div style={{ width: `${Full_Game.full_home_win_prob * 100}%` }} className="bg-red-500 h-full"></div>
                            </div>
                            <div className="text-xs font-black text-gray-400 w-8 text-left">{Math.round(Full_Game.full_home_win_prob * 100)}%</div>
                        </div>

                        {/* ML ODDS (Bookie Kelimesi Çıkarıldı, O/U Barem eklendi) */}
                        <div className="bg-slate-900/60 border border-slate-700 rounded-lg px-4 py-2 w-full max-w-[240px] flex items-center justify-between relative">
                            {/* O/U Barem */}
                            <div className="absolute -top-3 right-3 bg-slate-800 border border-slate-600 px-2 py-0.5 rounded text-[10px] font-bold text-gray-300">
                                O/U: {Odds.over_under}
                            </div>

                            {/* ML Başlığı ve Oranlar */}
                            <div className="flex flex-col items-center w-1/3">
                                <span className={`text-base font-black ${Odds.away_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-200'}`}>
                                    {formatAmericanOdds(Odds.best_away_odds)}
                                </span>
                            </div>
                            <div className="text-xs font-bold text-gray-500 uppercase tracking-widest px-2">ML</div>
                            <div className="flex flex-col items-center w-1/3">
                                <span className={`text-base font-black ${Odds.home_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-200'}`}>
                                    {formatAmericanOdds(Odds.best_home_odds)}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* ALT BİLGİ VE BUTONLAR */}
                <div className="mt-6 pt-4 border-t border-gray-700/50 flex flex-wrap justify-between items-center gap-3">
                    <div className="flex items-center gap-2">
                        {Details?.value_alerts?.length > 0 && (
                            <span className="animate-pulse bg-green-900/20 border border-mlb-green/40 px-2 py-1 rounded text-mlb-green text-[10px] font-black uppercase flex items-center">
                                🔥 Edge
                            </span>
                        )}
                    </div>

                    {/* Tyle'ın İstediği Yan Yana Butonlar */}
                    <div className="flex items-center gap-3">
                        <span className="text-gray-400 text-sm font-semibold cursor-pointer hover:text-white transition-colors">
                            In Depth 📊
                        </span>
                        <button
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="text-xs bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded transition-colors flex items-center gap-1 font-bold"
                        >
                            {isExpanded ? 'Hide Details ⬆' : 'Details ⬇'}
                        </button>
                    </div>
                </div>
            </div>

            {/* 3. EXPAND (GENİŞLETİLMİŞ DETAY) ALANI */}
            <div className={`bg-slate-900/95 border-t border-slate-700 overflow-hidden transition-all duration-300 ${isExpanded ? 'max-h-[1200px] opacity-100 p-4 md:p-6' : 'max-h-0 opacity-0 p-0'}`}>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

                    {/* YENİ: IMG_3226 Tarzı NRFI/YRFI Probability Card */}
                    <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700 shadow-inner">
                        <div className="flex justify-between items-start mb-4">
                            <div>
                                <h3 className={`text-xl font-black ${NRFI.pick === 'NRFI' ? 'text-blue-400' : 'text-red-400'}`}>
                                    {Math.round(NRFI.confidence * 100)}%
                                </h3>
                                <p className={`text-xs font-bold uppercase tracking-widest ${NRFI.pick === 'NRFI' ? 'text-blue-500' : 'text-red-500'}`}>
                                    {NRFI.pick} Probability
                                </p>
                            </div>
                        </div>

                        <div className="flex justify-between items-center text-center">
                            {/* Deplasman Pitcher Sabermetrics */}
                            <div className="w-1/3 flex flex-col items-center">
                                <img src={getTeamLogo(matchup.away_team)} alt="Away" className="w-8 h-8 opacity-70 mb-1" />
                                <div className="bg-slate-900 px-3 py-1 rounded-full text-xs font-bold text-gray-300 border border-slate-700 mb-2">
                                    {pitcherAway.fip} FIP
                                </div>
                                <div className="bg-slate-900 px-3 py-1 rounded-full text-xs font-bold text-gray-300 border border-slate-700">
                                    {Math.round(pitcherAway.k_bb_pct * 100)}% K-BB
                                </div>
                            </div>

                            {/* Orta Kısım */}
                            <div className="w-1/3 text-xs text-gray-500 font-bold uppercase flex flex-col gap-4">
                                <span>Pitcher Skills</span>
                                <span>Edge</span>
                            </div>

                            {/* Ev Sahibi Pitcher Sabermetrics */}
                            <div className="w-1/3 flex flex-col items-center">
                                <img src={getTeamLogo(matchup.home_team)} alt="Home" className="w-8 h-8 opacity-70 mb-1" />
                                <div className="bg-slate-900 px-3 py-1 rounded-full text-xs font-bold text-gray-300 border border-slate-700 mb-2">
                                    {pitcherHome.fip} FIP
                                </div>
                                <div className="bg-slate-900 px-3 py-1 rounded-full text-xs font-bold text-gray-300 border border-slate-700">
                                    {Math.round(pitcherHome.k_bb_pct * 100)}% K-BB
                                </div>
                            </div>
                        </div>

                        <div className="mt-4 pt-3 border-t border-slate-700/50 text-center">
                            <span className="text-sm font-black text-gray-400">Model Outcome: <span className={NRFI.pick === 'NRFI' ? 'text-blue-400' : 'text-red-400'}>{NRFI.pick}</span></span>
                        </div>
                    </div>

                    {/* F5 & Totals Card */}
                    <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700 shadow-inner">
                        <h3 className="text-xs text-gray-400 font-bold uppercase mb-4 border-b border-slate-700 pb-2">F5 & Totals Projection</h3>
                        <div className="flex justify-between text-sm mb-3 items-center">
                            <span className="text-gray-400 font-medium">F5 Score:</span>
                            <span className="font-bold text-white bg-slate-900 px-3 py-1 rounded border border-slate-700">
                                {F5.f5_away_score} - {F5.f5_home_score}
                            </span>
                        </div>
                        <div className="flex justify-between text-sm mb-3 items-center">
                            <span className="text-gray-400 font-medium">Model O/U Total:</span>
                            <span className="font-bold text-white bg-slate-900 px-3 py-1 rounded border border-slate-700">
                                {Full_Game.full_total} runs
                            </span>
                        </div>
                        <div className="flex justify-between text-sm items-center">
                            <span className="text-gray-400 font-medium">Total Difference:</span>
                            <span className={`font-bold px-2 py-1 rounded ${Full_Game.full_total > Odds.over_under ? 'bg-red-900/30 text-red-400' : 'bg-blue-900/30 text-blue-400'}`}>
                                {Math.abs(Full_Game.full_total - Odds.over_under).toFixed(1)} {Full_Game.full_total > Odds.over_under ? 'Over' : 'Under'} Bookie
                            </span>
                        </div>
                    </div>

                    {/* Detailed Weather Card (Span 2 columns on mobile, 1 on desktop) */}
                    <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700 shadow-inner md:col-span-2 flex flex-col md:flex-row items-center justify-between">
                        <div>
                            <h3 className="text-xs text-gray-400 font-bold uppercase mb-2">Ballpark Weather Context</h3>
                            {Weather ? (
                                <>
                                    <div className="text-xl font-black text-white flex items-center gap-2 mb-1">
                                        {getWeatherIcon(Weather.condition)} {Weather.temp_f}°F
                                    </div>
                                    <div className="text-sm text-gray-300">
                                        <span className="text-gray-500 mr-1">Wind:</span> {Weather.wind_mph} mph ({Weather.wind_direction})
                                    </div>
                                    <div className="text-sm text-gray-300">
                                        <span className="text-gray-500 mr-1">Condition:</span> {Weather.condition}
                                    </div>
                                </>
                            ) : (
                                <span className="text-sm text-gray-500">Weather data unavailable</span>
                            )}
                        </div>

                        <div className="text-5xl opacity-20 mt-4 md:mt-0">
                            {Weather?.wind_mph > 10 ? '💨' : '🏟️'}
                        </div>
                    </div>

                </div>
            </div>

        </div>
    );
};

export default MatchupCard;