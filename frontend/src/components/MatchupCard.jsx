import React, { useState } from 'react';
import { formatAmericanOdds, getTeamLogo } from '../utils/formatters';

// Hava durumu durumuna göre ikon döndüren yardımcı fonksiyon
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
    // Expand (Genişlet) durumu için state
    const [isExpanded, setIsExpanded] = useState(false);

    const { matchup, NRFI, F5, Full_Game, Details, Odds, Weather } = prediction;
    const pitcherAway = Details?.pitcher_analysis?.away || {};
    const pitcherHome = Details?.pitcher_analysis?.home || {};

    return (
        <div className="bg-mlb-card rounded-xl border border-gray-700 shadow-2xl overflow-hidden mb-6 transition-all duration-300 hover:border-gray-500">

            {/* 1. ÜST BAR: Takımlar, Lig ve Hava Durumu Özeti */}
            <div className="bg-slate-800/80 px-3 md:px-4 py-2 flex justify-between items-center text-[10px] md:text-xs text-gray-400 font-bold uppercase tracking-wider">
                <span className="truncate pr-2">{matchup.away_team} @ {matchup.home_team}</span>
                <div className="flex items-center gap-3">
                    {/* Hava Durumu Mini İkonu */}
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
                <div className="flex flex-wrap md:flex-nowrap items-start md:items-center justify-between">

                    {/* DEPLASMAN TAKIMI */}
                    <div className="flex flex-col items-center w-1/2 md:w-1/3 order-1 text-center px-1">
                        <img src={getTeamLogo(matchup.away_team)} alt={matchup.away_team} className="w-14 h-14 md:w-16 md:h-16 mb-2 drop-shadow-lg" />
                        <h2 className="text-base md:text-xl font-black leading-tight">{matchup.away_team}</h2>
                        {/* Takım Kaydı eklendi */}
                        <span className="text-[10px] text-gray-400 font-semibold mb-2">{matchup.away_stats?.record}</span>

                        <div className="bg-slate-800/50 rounded px-2 py-1 w-full max-w-[120px]">
                            <p className="text-[10px] md:text-xs text-gray-300 truncate font-bold">{matchup.away_pitcher}</p>
                            {/* Atıcı W-L ve ERA eklendi */}
                            <p className="text-[9px] text-gray-400">{pitcherAway.record} | {pitcherAway.era} ERA</p>
                        </div>
                    </div>

                    {/* EV SAHİBİ TAKIMI */}
                    <div className="flex flex-col items-center w-1/2 md:w-1/3 order-2 md:order-3 text-center px-1">
                        <img src={getTeamLogo(matchup.home_team)} alt={matchup.home_team} className="w-14 h-14 md:w-16 md:h-16 mb-2 drop-shadow-lg" />
                        <h2 className="text-base md:text-xl font-black leading-tight">{matchup.home_team}</h2>
                        {/* Takım Kaydı eklendi */}
                        <span className="text-[10px] text-gray-400 font-semibold mb-2">{matchup.home_stats?.record}</span>

                        <div className="bg-slate-800/50 rounded px-2 py-1 w-full max-w-[120px]">
                            <p className="text-[10px] md:text-xs text-gray-300 truncate font-bold">{matchup.home_pitcher}</p>
                            {/* Atıcı W-L ve ERA eklendi */}
                            <p className="text-[9px] text-gray-400">{pitcherHome.record} | {pitcherHome.era} ERA</p>
                        </div>
                    </div>

                    {/* ORTA ALAN: Skor, ML Oranlar ve Bookie O/U */}
                    <div className="flex flex-col items-center w-full md:w-1/3 order-3 md:order-2 mt-6 md:mt-0 pt-5 md:pt-0 border-t border-gray-700/50 md:border-0">

                        {/* MODEL SKOR TAHMİNİ (Yeni Eklendi) */}
                        <div className="text-center mb-3">
                            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest block mb-1">Proj. Score</span>
                            <div className="text-2xl md:text-3xl font-black text-white bg-slate-900/40 px-4 py-1 rounded-lg border border-slate-700">
                                {Full_Game.full_away_score} <span className="text-gray-600 font-normal mx-1">-</span> {Full_Game.full_home_score}
                            </div>
                        </div>

                        {/* WIN PROBABILITIES */}
                        <div className="flex items-center gap-2 mb-3">
                            <div className="text-xs md:text-sm font-black text-gray-300">
                                {Math.round(Full_Game.full_away_win_prob * 100)}%
                            </div>
                            <div className="w-16 h-1 bg-gray-700 rounded-full overflow-hidden flex">
                                <div style={{ width: `${Full_Game.full_away_win_prob * 100}%` }} className="bg-blue-500 h-full"></div>
                                <div style={{ width: `${Full_Game.full_home_win_prob * 100}%` }} className="bg-red-500 h-full"></div>
                            </div>
                            <div className="text-xs md:text-sm font-black text-gray-300">
                                {Math.round(Full_Game.full_home_win_prob * 100)}%
                            </div>
                        </div>

                        {/* BOOKIE O/U & ODDS */}
                        <div className="bg-slate-900/50 border border-slate-700/50 rounded-lg px-4 py-2 w-full max-w-[220px] flex flex-col items-center">
                            <div className="text-gray-400 text-[10px] md:text-xs font-bold uppercase tracking-widest mb-1 flex justify-between w-full">
                                <span>Bookie O/U:</span>
                                <span className="text-white">{Odds.over_under}</span>
                            </div>
                            <div className="flex justify-between w-full mt-1">
                                <span className={`text-sm font-black ${Odds.away_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-300'}`}>
                                    {formatAmericanOdds(Odds.best_away_odds)}
                                </span>
                                <span className="text-gray-600 font-light">|</span>
                                <span className={`text-sm font-black ${Odds.home_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-300'}`}>
                                    {formatAmericanOdds(Odds.best_home_odds)}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* ALT BİLGİ VE EXPAND BUTONU */}
                <div className="mt-5 pt-3 border-t border-gray-700/50 flex flex-wrap justify-between items-center gap-3">
                    <div className="flex items-center gap-3">
                        <div className="text-[10px] flex items-center bg-gray-800/50 px-2 py-1 rounded border border-gray-700">
                            <span className="text-gray-400 font-bold mr-2">1ST INNING:</span>
                            <span className={`px-2 py-0.5 rounded font-black ${NRFI.pick === 'NRFI' ? 'bg-blue-900/40 text-blue-400' : 'bg-red-900/40 text-red-400'}`}>
                                {NRFI.pick} ({Math.round(NRFI.confidence * 100)}%)
                            </span>
                        </div>
                        {Details?.value_alerts?.length > 0 && (
                            <span className="animate-pulse text-mlb-green text-[10px] font-black uppercase flex items-center">
                                🔥 Edge Detected
                            </span>
                        )}
                    </div>

                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="text-xs bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded transition-colors flex items-center gap-1 font-bold"
                    >
                        {isExpanded ? 'Hide Details ⬆' : 'Details ⬇'}
                    </button>
                </div>
            </div>

            {/* 3. EXPAND (GENİŞLETİLMİŞ DETAY) ALANI */}
            <div className={`bg-slate-900/90 border-t border-slate-700 overflow-hidden transition-all duration-300 ${isExpanded ? 'max-h-[1000px] opacity-100 p-4 md:p-6' : 'max-h-0 opacity-0 p-0'}`}>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                    {/* F5 & Totals Card */}
                    <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                        <h3 className="text-xs text-gray-400 font-bold uppercase mb-3 border-b border-slate-700 pb-1">F5 & Totals Projection</h3>
                        <div className="flex justify-between text-sm mb-2">
                            <span className="text-gray-300">F5 Score:</span>
                            <span className="font-bold text-white">{F5.f5_away_score} - {F5.f5_home_score}</span>
                        </div>
                        <div className="flex justify-between text-sm mb-2">
                            <span className="text-gray-300">Model O/U Total:</span>
                            <span className="font-bold text-white">{Full_Game.full_total} runs</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-300">Total Difference:</span>
                            <span className={`font-bold ${Full_Game.full_total > Odds.over_under ? 'text-blue-400' : 'text-red-400'}`}>
                                {Math.abs(Full_Game.full_total - Odds.over_under).toFixed(1)} {Full_Game.full_total > Odds.over_under ? 'Over' : 'Under'} Bookie
                            </span>
                        </div>
                    </div>

                    {/* Advanced Pitching Card */}
                    <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                        <h3 className="text-xs text-gray-400 font-bold uppercase mb-3 border-b border-slate-700 pb-1">Advanced Pitching (Sabermetrics)</h3>
                        <div className="flex justify-between text-sm mb-2">
                            <span className="text-gray-300">{matchup.away_pitcher}:</span>
                            <span className="font-bold text-white">{pitcherAway.fip} FIP | {Math.round(pitcherAway.k_bb_pct * 100)}% K-BB</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-300">{matchup.home_pitcher}:</span>
                            <span className="font-bold text-white">{pitcherHome.fip} FIP | {Math.round(pitcherHome.k_bb_pct * 100)}% K-BB</span>
                        </div>
                    </div>

                    {/* Team Form (L10) Card */}
                    <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
                        <h3 className="text-xs text-gray-400 font-bold uppercase mb-3 border-b border-slate-700 pb-1">Team Form</h3>
                        <div className="flex justify-between text-sm mb-2">
                            <span className="text-gray-300">{matchup.away_team} (Away):</span>
                            <span className="font-bold text-white">{matchup.away_stats?.away_record} | L10: {matchup.away_stats?.l10}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-300">{matchup.home_team} (Home):</span>
                            <span className="font-bold text-white">{matchup.home_stats?.home_record} | L10: {matchup.home_stats?.l10}</span>
                        </div>
                    </div>

                    {/* Detailed Weather Card */}
                    <div className="bg-slate-800 rounded-lg p-3 border border-slate-700 flex items-center justify-between">
                        <div>
                            <h3 className="text-xs text-gray-400 font-bold uppercase mb-2">Ballpark Weather</h3>
                            {Weather ? (
                                <>
                                    <div className="text-lg font-black text-white flex items-center gap-2">
                                        {getWeatherIcon(Weather.condition)} {Weather.temp_f}°F
                                    </div>
                                    <div className="text-xs text-gray-400 mt-1">Wind: {Weather.wind_mph} mph ({Weather.wind_direction})</div>
                                    <div className="text-xs text-gray-400">Condition: {Weather.condition}</div>
                                </>
                            ) : (
                                <span className="text-sm text-gray-500">Weather data unavailable</span>
                            )}
                        </div>
                        {/* Dekoratif Rüzgar İkonu (Covers/RudeBets tarzı hissiyat) */}
                        <div className="text-4xl opacity-20">
                            {Weather?.wind_mph > 10 ? '💨' : '🏟️'}
                        </div>
                    </div>

                </div>
            </div>

        </div>
    );
};

export default MatchupCard;