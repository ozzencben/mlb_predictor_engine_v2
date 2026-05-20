import React, { useState } from 'react';
import { formatAmericanOdds, getTeamLogo } from '../utils/formatters';
import SportsbookLogo from './SportsbookLogo';

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

// NRFI yüzdesi için dinamik renk
const getNrfiColor = (pct) => {
    if (pct === 'N/A' || !pct) return 'bg-slate-800 text-gray-500 border-slate-700';
    if (pct >= 70) return 'bg-red-500/20 text-red-400 border-red-500/30'; // Hot
    if (pct <= 40) return 'bg-blue-500/20 text-blue-400 border-blue-500/30'; // Cold
    return 'bg-slate-700 text-gray-300 border-slate-600'; // Neutral
};

const getEraClass = (era) => {
    if (!era || era === 'N/A' || era === '-') return 'text-gray-400 font-bold';
    const val = parseFloat(era);
    if (isNaN(val)) return 'text-gray-400 font-bold';
    if (val < 3.00) return 'text-green-400 font-extrabold';
    if (val > 3.00) return 'text-red-400 font-extrabold';
    return 'text-gray-200 font-bold';
};

const renderNrfiStat = (pct, record, isFallback) => {
    if (isFallback) {
        return (
            <span className="text-[8px] font-bold text-slate-600 italic">N/A</span>
        );
    }
    if (pct === 'N/A' || pct === undefined || pct === null) return <span className="text-gray-600 font-bold text-xs">-</span>;
    return (
        <div className="flex flex-col items-center justify-center">
            <span className={`px-1.5 md:px-2 py-0.5 rounded text-[10px] md:text-xs font-black border tracking-wider shadow-sm ${getNrfiColor(pct)}`}>
                {pct}%
            </span>
            {record && record !== "0-0" && <span className="text-[8px] md:text-[9px] text-gray-400 font-bold mt-1 tracking-wider whitespace-nowrap">{record}</span>}
        </div>
    );
};

const MatchupCard = ({ prediction }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const { matchup, NRFI, F5, Full_Game, Details, Odds, Weather } = prediction;
    const pitcherAway = Details?.pitcher_analysis?.away || {};
    const pitcherHome = Details?.pitcher_analysis?.home || {};
    const isLive = matchup.status === "In Progress";

    // AI Insight Verisi
    const aiInsight = Details?.ai_insight;

    // Yeni Trend Verilerini Çıkar (Fallback güvenliği ile)
    const trends = NRFI?.scraped_trends || {};
    const isFallback = trends?.is_fallback === true;
    const awayTrends = trends?.away_pitcher || {};
    const homeTrends = trends?.home_pitcher || {};
    const awayTeamNrfi = trends?.away_team_nrfi || {};
    const homeTeamNrfi = trends?.home_team_nrfi || {};
    const isTrendsFallback = trends?.is_fallback ?? true;

    // Atıcının bu sezon verisi yoksa (Lig Ort. ile doldurulmuş - Zach Thornton gibi)
    const awayPitcherNoData = awayTrends?.season_record === '0-0' && !isFallback;
    const homePitcherNoData = homeTrends?.season_record === '0-0' && !isFallback;

    // Odds Barem Güvenlik Kontrolü
    const isOddsAvailable = Odds && Odds.over_under > 0;

    return (
        <div className="bg-mlb-card rounded-xl border border-gray-700 shadow-2xl overflow-hidden mb-8 transition-all duration-300 hover:border-gray-500 w-full">

            {/* ================= 1. ÜST BAR ================= */}
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
                    {Weather && Weather.cbs_alert_word && Weather.cbs_alert_word !== "Clear" && (
                        <span className={`px-1.5 md:px-2 py-1 rounded text-[8px] md:text-[10px] font-black uppercase tracking-widest border flex items-center gap-1 shadow-sm ${Weather.red_flag_alert ? 'bg-red-900/80 text-red-100 border-red-500' : (Weather.cbs_alert_word.includes('Ideal') ? 'bg-green-900/50 text-green-300 border-green-500/50' : 'bg-amber-900/50 text-amber-300 border-amber-500/50')}`}>
                            {Weather.red_flag_alert ? '🚩' : (Weather.cbs_alert_word.includes('Ideal') ? '✅' : '⚠️')}
                            <span className="whitespace-nowrap">{Weather.cbs_alert_word}</span>
                        </span>
                    )}
                    {Weather && (
                        <span className="flex items-center gap-1 text-gray-200 bg-slate-900/80 px-2 py-1 rounded border border-slate-600 shadow-sm text-[9px] md:text-[10px] font-bold whitespace-nowrap">
                            {getWeatherIcon(Weather.condition)} {Weather.temp_f}°F
                        </span>
                    )}
                </div>
            </div>

            {/* ================= 2. ANA KART İÇERİĞİ ================= */}
            <div className="p-3 md:p-6">

                {/* ================= SABERMETRİK ANOMALİ UYARI KUTUSU ================= */}
                {Details?.model_anomalies && Details.model_anomalies.length > 0 && (
                    <div className="bg-amber-500/10 border border-amber-500/25 rounded-xl p-3 md:p-4 mb-5 flex items-start gap-3 shadow-[0_0_15px_rgba(245,158,11,0.05)]">
                        <span className="text-amber-400 text-lg leading-none mt-0.5">⚠️</span>
                        <div className="flex-1 min-w-0">
                            <h4 className="text-[10px] md:text-xs text-amber-400 font-black uppercase tracking-wider mb-1">
                                Sabermetric Adjustments Applied
                            </h4>
                            <ul className="list-disc list-inside space-y-0.5">
                                {Details.model_anomalies.map((anomaly, idx) => (
                                    <li key={idx} className="text-[9px] md:text-[11px] text-gray-300 font-medium">
                                        {anomaly}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                )}

                {/* LOGOLAR, SAAT VE ATICILAR */}
                <div className="flex w-full justify-between items-start mb-5 gap-1">
                    {/* DEPLASMAN */}
                    <div className="flex-1 flex flex-col items-center text-center w-0 px-0.5">
                        <img src={getTeamLogo(matchup.away_team)} alt={matchup.away_team} className="w-11 h-11 xs:w-14 xs:h-14 md:w-20 md:h-20 mb-2 drop-shadow-lg" />
                        <div className="min-h-[40px] md:min-h-[48px] flex items-center justify-center w-full mb-2">
                            <h2 className="text-[10px] xs:text-[13px] md:text-lg font-black leading-tight balance-text whitespace-normal break-words">{matchup.away_team}</h2>
                        </div>
                        <div className="bg-slate-800/80 border border-slate-700 rounded-lg px-1 xs:px-2 py-1.5 w-full max-w-[110px] xs:max-w-[130px] md:max-w-[165px] shadow-inner mx-auto relative">
                            {pitcherAway.is_fallback && (
                                <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[7px] font-black px-1 py-0.5 rounded uppercase tracking-wider shadow animate-pulse whitespace-nowrap">
                                    ⚠️ Fallback SP
                                </span>
                            )}
                            <p className={`text-[9px] xs:text-[11px] md:text-xs text-gray-200 font-bold whitespace-normal break-words leading-tight ${pitcherAway.is_fallback ? 'mt-1' : ''}`}>{matchup.away_pitcher}</p>
                            <div className="text-[8px] xs:text-[10px] text-gray-400 mt-1 font-semibold leading-tight flex flex-col xs:flex-row items-center justify-center gap-0.5 xs:gap-1.5">
                                <span>({pitcherAway.record || '0-0'})</span>
                                <span className="hidden xs:inline text-gray-500">|</span>
                                <span className={getEraClass(pitcherAway.era)}>{pitcherAway.era || '0.00'} ERA</span>
                            </div>
                        </div>
                    </div>

                    {/* ORTA: SAAT */}
                    <div className="flex-shrink-0 flex flex-col items-center justify-start pt-2 px-0.5">
                        <span className="text-[7px] xs:text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1 text-center">Game Time</span>
                        <span className="text-[9px] xs:text-xs md:text-sm font-black text-gray-300 bg-slate-900/50 px-2 py-1 rounded-full border border-slate-700/50 whitespace-nowrap">
                            {matchup.game_time || "TBD"}
                        </span>
                    </div>

                    {/* EV SAHİBİ */}
                    <div className="flex-1 flex flex-col items-center text-center w-0 px-0.5">
                        <img src={getTeamLogo(matchup.home_team)} alt={matchup.home_team} className="w-11 h-11 xs:w-14 xs:h-14 md:w-20 md:h-20 mb-2 drop-shadow-lg" />
                        <div className="min-h-[40px] md:min-h-[48px] flex items-center justify-center w-full mb-2">
                            <h2 className="text-[10px] xs:text-[13px] md:text-lg font-black leading-tight balance-text whitespace-normal break-words">{matchup.home_team}</h2>
                        </div>
                        <div className="bg-slate-800/80 border border-slate-700 rounded-lg px-1 xs:px-2 py-1.5 w-full max-w-[110px] xs:max-w-[130px] md:max-w-[165px] shadow-inner mx-auto relative">
                            {pitcherHome.is_fallback && (
                                <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[7px] font-black px-1 py-0.5 rounded uppercase tracking-wider shadow animate-pulse whitespace-nowrap">
                                    ⚠️ Fallback SP
                                </span>
                            )}
                            <p className={`text-[9px] xs:text-[11px] md:text-xs text-gray-200 font-bold whitespace-normal break-words leading-tight ${pitcherHome.is_fallback ? 'mt-1' : ''}`}>{matchup.home_pitcher}</p>
                            <div className="text-[8px] xs:text-[10px] text-gray-400 mt-1 font-semibold leading-tight flex flex-col xs:flex-row items-center justify-center gap-0.5 xs:gap-1.5">
                                <span>({pitcherHome.record || '0-0'})</span>
                                <span className="hidden xs:inline text-gray-500">|</span>
                                <span className={getEraClass(pitcherHome.era)}>{pitcherHome.era || '0.00'} ERA</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* COVERS STİLİ STACKED KAYITLAR */}
                <div className="flex justify-center items-center w-full mb-6 bg-slate-900/40 rounded-lg py-3 border border-slate-700/50 max-w-[320px] mx-auto shadow-inner px-2">
                    <div className="flex flex-col flex-1 text-right pr-3 md:pr-4 gap-2">
                        <span className="text-[10px] md:text-[11px] font-black text-gray-300">{matchup.away_stats?.record || "0-0"}</span>
                        <span className="text-[10px] md:text-[11px] font-black text-gray-400">{matchup.away_stats?.away_record || "0-0"}</span>
                        <span className="text-[10px] md:text-[11px] font-black text-gray-400">{matchup.away_stats?.l10 || "0-0"}</span>
                    </div>
                    <div className="flex flex-col flex-shrink-0 text-center gap-2 border-x border-slate-700/50 px-3 md:px-4">
                        <span className="text-[8px] md:text-[9px] text-gray-500 font-black uppercase tracking-widest">Overall</span>
                        <span className="text-[8px] md:text-[9px] text-gray-500 font-black uppercase tracking-widest">A/H</span>
                        <span className="text-[8px] md:text-[9px] text-gray-500 font-black uppercase tracking-widest">L 10</span>
                    </div>
                    <div className="flex flex-col flex-1 text-left pl-3 md:pl-4 gap-2">
                        <span className="text-[10px] md:text-[11px] font-black text-gray-300">{matchup.home_stats?.record || "0-0"}</span>
                        <span className="text-[10px] md:text-[11px] font-black text-gray-400">{matchup.home_stats?.home_record || "0-0"}</span>
                        <span className="text-[10px] md:text-[11px] font-black text-gray-400">{matchup.home_stats?.l10 || "0-0"}</span>
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
                    <div className="bg-slate-900/80 border border-slate-700 rounded-xl px-4 pt-4 pb-3 w-full max-w-[290px] flex items-center justify-between relative shadow-lg">
                        <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-slate-800 border border-slate-600 px-4 py-0.5 rounded-full text-[10px] font-black text-gray-300 shadow-md whitespace-nowrap">
                            Book O/U: {isOddsAvailable ? Odds.over_under : 'N/A'}
                        </div>

                        <div className="flex flex-col items-center w-2/5 min-w-0">
                            <span className={`text-lg xs:text-xl font-black tracking-tight truncate ${Odds.away_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-200'}`}>
                                {formatAmericanOdds(Odds.best_away_odds)}
                            </span>
                            {Odds.away_book && (
                                <div className="mt-1 flex items-center gap-1 max-w-full justify-center">
                                    <SportsbookLogo bookmaker={Odds.away_book} size="xs" />
                                    <span className="text-[8px] text-gray-500 font-bold uppercase truncate max-w-[55px] xs:max-w-[75px] md:max-w-none">{Odds.away_book}</span>
                                </div>
                            )}
                        </div>
                        <div className="text-[10px] font-bold text-gray-600 uppercase tracking-widest w-1/5 text-center flex-shrink-0">ML</div>
                        <div className="flex flex-col items-center w-2/5 min-w-0">
                            <span className={`text-lg xs:text-xl font-black tracking-tight truncate ${Odds.home_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-200'}`}>
                                {formatAmericanOdds(Odds.best_home_odds)}
                            </span>
                            {Odds.home_book && (
                                <div className="mt-1 flex items-center gap-1 max-w-full justify-center">
                                    <SportsbookLogo bookmaker={Odds.home_book} size="xs" />
                                    <span className="text-[8px] text-gray-500 font-bold uppercase truncate max-w-[55px] xs:max-w-[75px] md:max-w-none">{Odds.home_book}</span>
                                </div>
                            )}
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
            <div className={`bg-slate-900 border-t border-slate-700 overflow-hidden transition-all duration-500 ease-in-out ${isExpanded ? 'max-h-[2000px] opacity-100 p-4 md:p-6' : 'max-h-0 opacity-0 p-0'}`}>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">

                    {/* NRFI/YRFI TABLE CARD */}
                    <div className="bg-slate-800/60 rounded-xl overflow-hidden border border-slate-700/80 flex flex-col h-full shadow-lg">
                        {/* Header: Probability */}
                        <div className="p-4 md:p-5 flex justify-between items-center bg-slate-800/90 border-b border-slate-700">
                            <div>
                                <h3 className={`text-3xl md:text-4xl font-black tracking-tighter leading-none ${NRFI.pick === 'NRFI' ? 'text-mlb-green' : 'text-red-400'}`}>
                                    {Math.round(NRFI.confidence * 100)}%
                                </h3>
                                <p className={`text-[9px] font-black uppercase tracking-widest mt-1 ${NRFI.pick === 'NRFI' ? 'text-mlb-green/80' : 'text-red-500/80'}`}>
                                    {NRFI.pick} Probability
                                </p>
                            </div>
                            <div className="text-right flex flex-col items-end">
                                <span className="text-[9px] font-bold text-gray-500 uppercase tracking-widest block mb-1">Outcome</span>
                                <div className={`text-sm font-black italic border px-3 py-1 rounded-md shadow-inner ${NRFI.pick === 'NRFI' ? 'text-mlb-green border-mlb-green/30 bg-green-900/20' : 'text-red-400 border-red-500/30 bg-red-900/20'}`}>
                                    {NRFI.pick}
                                </div>
                            </div>
                        </div>

                        {/* Pitcher NRFI Table */}
                        <div className="w-full bg-slate-900/40">
                            {/* Table Header */}
                            <div className="flex justify-between items-center bg-slate-900/80 px-2 md:px-3 py-2 border-b border-slate-700/50">
                                <div className="text-[8px] md:text-[10px] font-black text-gray-400 uppercase tracking-widest w-[40%] text-left pl-1 flex items-center gap-1.5">
                                    Pitcher NRFI
                                    {isFallback && <span className="text-[6px] font-black text-amber-500 bg-amber-500/10 border border-amber-500/20 px-1 py-0.5 rounded uppercase tracking-wider">⚠️ No Data</span>}
                                </div>
                                <div className="text-[8px] md:text-[10px] font-black text-gray-400 uppercase tracking-widest w-[20%] text-center">Season</div>
                                <div className="text-[8px] md:text-[10px] font-black text-gray-400 uppercase tracking-widest w-[20%] text-center">Location</div>
                                <div className="text-[8px] md:text-[10px] font-black text-gray-400 uppercase tracking-widest w-[20%] text-center">Last 10</div>
                            </div>

                            {/* Away Pitcher Row */}
                            <div className="flex justify-between items-center px-2 md:px-3 py-2.5 md:py-3 border-b border-slate-700/30 hover:bg-slate-800/30 transition-colors">
                                <div className="flex items-center gap-1.5 md:gap-2 w-[40%] min-w-0 pr-1">
                                    <img src={getTeamLogo(matchup.away_team)} alt={matchup.away_team} className="w-5 h-5 md:w-8 md:h-8 drop-shadow-md flex-shrink-0" />
                                    <div className="flex flex-col min-w-0">
                                        <span className="text-[10px] md:text-sm font-black text-gray-200 truncate">{matchup.away_pitcher}</span>
                                        {awayPitcherNoData ? (
                                            <span className="text-[7px] font-black text-amber-500/80 bg-amber-500/10 border border-amber-500/20 px-1 py-0.5 rounded uppercase tracking-wider leading-none mt-0.5 w-fit">Lig Ort.</span>
                                        ) : !isFallback && awayTrends.streak_score > 0 ? (
                                            <span className="text-[8px] md:text-[10px] font-bold text-gray-400 flex items-center gap-0.5 md:gap-1 mt-0.5">
                                                {awayTrends.streak_emoji} <span className="text-white font-black">{awayTrends.streak_score}W</span>
                                            </span>
                                        ) : (
                                            <span className="text-[8px] font-medium text-gray-600 mt-0.5">-</span>
                                        )}
                                    </div>
                                </div>
                                <div className="w-[20%] flex justify-center">{renderNrfiStat(awayTrends.season_nrfi_pct, awayTrends.season_record, isFallback)}</div>
                                <div className="w-[20%] flex justify-center">{renderNrfiStat(awayTrends.location_nrfi_pct, awayTrends.location_record, isFallback)}</div>
                                <div className="w-[20%] flex justify-center">{renderNrfiStat(awayTrends.last10_nrfi_pct, awayTrends.last10_record, isFallback)}</div>
                            </div>

                            {/* Home Pitcher Row */}
                            <div className="flex justify-between items-center px-2 md:px-3 py-2.5 md:py-3 hover:bg-slate-800/30 transition-colors">
                                <div className="flex items-center gap-1.5 md:gap-2 w-[40%] min-w-0 pr-1">
                                    <img src={getTeamLogo(matchup.home_team)} alt={matchup.home_team} className="w-5 h-5 md:w-8 md:h-8 drop-shadow-md flex-shrink-0" />
                                    <div className="flex flex-col min-w-0">
                                        <span className="text-[10px] md:text-sm font-black text-gray-200 truncate">{matchup.home_pitcher}</span>
                                        {homePitcherNoData ? (
                                            <span className="text-[7px] font-black text-amber-500/80 bg-amber-500/10 border border-amber-500/20 px-1 py-0.5 rounded uppercase tracking-wider leading-none mt-0.5 w-fit">Lig Ort.</span>
                                        ) : !isFallback && homeTrends.streak_score > 0 ? (
                                            <span className="text-[8px] md:text-[10px] font-bold text-gray-400 flex items-center gap-0.5 md:gap-1 mt-0.5">
                                                {homeTrends.streak_emoji} <span className="text-white font-black">{homeTrends.streak_score}W</span>
                                            </span>
                                        ) : (
                                            <span className="text-[8px] font-medium text-gray-600 mt-0.5">-</span>
                                        )}
                                    </div>
                                </div>
                                <div className="w-[20%] flex justify-center">{renderNrfiStat(homeTrends.season_nrfi_pct, homeTrends.season_record, isFallback)}</div>
                                <div className="w-[20%] flex justify-center">{renderNrfiStat(homeTrends.location_nrfi_pct, homeTrends.location_record, isFallback)}</div>
                                <div className="w-[20%] flex justify-center">{renderNrfiStat(homeTrends.last10_nrfi_pct, homeTrends.last10_record, isFallback)}</div>
                            </div>
                        </div>

                        {/* Team NRFI Records Footer Table */}
                        <div className="w-full bg-slate-900/60 mt-auto border-t border-slate-700">
                            <div className="flex justify-between items-center bg-slate-800/40 px-2 md:px-3 py-1.5 border-b border-slate-700/50">
                                <div className="text-[7px] md:text-[9px] font-black text-gray-500 uppercase tracking-widest w-[30%] text-left pl-1 flex items-center gap-1.5">
                                    Team NRFI
                                    {isFallback && <span className="text-[6px] font-black text-amber-500 bg-amber-500/10 border border-amber-500/20 px-1 py-0.5 rounded uppercase">⚠️ N/A</span>}
                                </div>
                                <div className="text-[7px] md:text-[9px] font-black text-gray-500 uppercase tracking-widest w-[20%] text-center">Season</div>
                                <div className="text-[7px] md:text-[9px] font-black text-gray-500 uppercase tracking-widest w-[30%] text-center">Away/Home</div>
                                <div className="text-[7px] md:text-[9px] font-black text-gray-500 uppercase tracking-widest w-[20%] text-center">L10</div>
                            </div>
                            <div className="flex justify-between items-center px-2 md:px-4 py-2 border-b border-slate-700/30">
                                <div className="w-[30%] text-[9px] md:text-[10px] font-bold text-gray-400 flex items-center gap-1.5 min-w-0 pr-1"><span className="w-1.5 h-1.5 md:w-2 md:h-2 rounded-full bg-blue-500 flex-shrink-0"></span><span className="truncate">{matchup.away_team}</span></div>
                                <div className="w-[20%] flex justify-center">{renderNrfiStat(awayTeamNrfi.season_nrfi_pct, awayTeamNrfi.season_record, isFallback)}</div>
                                <div className="w-[30%] flex justify-center items-center"><span className="text-[8px] text-gray-500 font-bold mr-1">A</span>{renderNrfiStat(awayTeamNrfi.location_nrfi_pct, awayTeamNrfi.location_record, isFallback)}</div>
                                <div className="w-[20%] flex justify-center">{renderNrfiStat(awayTeamNrfi.last10_nrfi_pct, awayTeamNrfi.last10_record, isFallback)}</div>
                            </div>
                            <div className="flex justify-between items-center px-2 md:px-4 py-2">
                                <div className="w-[30%] text-[9px] md:text-[10px] font-bold text-gray-400 flex items-center gap-1.5 min-w-0 pr-1"><span className="w-1.5 h-1.5 md:w-2 md:h-2 rounded-full bg-red-500 flex-shrink-0"></span><span className="truncate">{matchup.home_team}</span></div>
                                <div className="w-[20%] flex justify-center">{renderNrfiStat(homeTeamNrfi.season_nrfi_pct, homeTeamNrfi.season_record, isFallback)}</div>
                                <div className="w-[30%] flex justify-center items-center"><span className="text-[8px] text-gray-500 font-bold mr-1">H</span>{renderNrfiStat(homeTeamNrfi.location_nrfi_pct, homeTeamNrfi.location_record, isFallback)}</div>
                                <div className="w-[20%] flex justify-center">{renderNrfiStat(homeTeamNrfi.last10_nrfi_pct, homeTeamNrfi.last10_record, isFallback)}</div>
                            </div>
                        </div>
                    </div>

                    {/* Right Column: Advanced Stats & Projections */}
                    <div className="flex flex-col gap-4">
                        {/* F5 & Totals Card */}
                        <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/80 flex flex-col justify-between flex-grow shadow-lg">
                            <div>
                                <h3 className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-4 border-b border-slate-700 pb-2">Game Projections</h3>


                                <div className="flex justify-between text-[11px] md:text-sm mb-4 items-center gap-2">
                                    <span className="text-gray-400 font-semibold leading-tight">F5 Score Proj:</span>
                                    <span className="font-black text-white bg-slate-900 px-3 md:px-4 py-1 md:py-1.5 rounded-lg border border-slate-700 text-xs md:text-lg shadow-inner whitespace-nowrap">
                                        {F5.f5_away_score} - {F5.f5_home_score}
                                    </span>
                                </div>
                                {isOddsAvailable && Odds.f5_away_odds !== 0.0 ? (
                                    <div className="flex justify-between text-[11px] md:text-sm mb-4 items-center bg-slate-900/50 p-2 md:p-3 rounded-lg border border-slate-700/50">
                                        <span className="text-gray-400 font-semibold leading-tight">Vegas F5 ML:</span>
                                        <div className="flex gap-3 xs:gap-4">
                                            <div className="flex flex-col items-center min-w-[50px]">
                                                <span className="text-[8px] xs:text-[10px] text-gray-500 font-black tracking-wider truncate max-w-[60px]">{matchup.away_team}</span>
                                                <span className={`font-black text-xs xs:text-sm md:text-base ${Odds.f5_away_edge_pct > 5 ? 'text-mlb-green' : 'text-white'}`}>{formatAmericanOdds(Odds.f5_away_odds)}</span>
                                                {Odds.f5_away_book && (
                                                    <div className="mt-0.5 flex items-center gap-0.5">
                                                        <SportsbookLogo bookmaker={Odds.f5_away_book} size="xs" />
                                                        <span className="text-[7px] text-gray-600 font-bold uppercase truncate max-w-[45px] xs:max-w-[65px] md:max-w-none">{Odds.f5_away_book}</span>
                                                    </div>
                                                )}
                                            </div>
                                            <div className="flex flex-col items-center min-w-[50px]">
                                                <span className="text-[8px] xs:text-[10px] text-gray-500 font-black tracking-wider truncate max-w-[60px]">{matchup.home_team}</span>
                                                <span className={`font-black text-xs xs:text-sm md:text-base ${Odds.f5_home_edge_pct > 5 ? 'text-mlb-green' : 'text-white'}`}>{formatAmericanOdds(Odds.f5_home_odds)}</span>
                                                {Odds.f5_home_book && (
                                                    <div className="mt-0.5 flex items-center gap-0.5">
                                                        <SportsbookLogo bookmaker={Odds.f5_home_book} size="xs" />
                                                        <span className="text-[7px] text-gray-600 font-bold uppercase truncate max-w-[45px] xs:max-w-[65px] md:max-w-none">{Odds.f5_home_book}</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex justify-between text-[11px] md:text-sm mb-4 items-center bg-slate-900/50 p-2 md:p-3 rounded-lg border border-slate-700/50">
                                        <span className="text-gray-400 font-semibold leading-tight">Vegas F5 ML:</span>
                                        <span className="text-[9px] font-black text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20 whitespace-nowrap">
                                            🔒 Locked
                                        </span>
                                    </div>
                                )}
                                <div className="flex justify-between text-[11px] md:text-sm mb-4 items-center gap-2">
                                    <span className="text-gray-400 font-semibold leading-tight">Model O/U Total:</span>
                                    <span className="font-black text-white bg-slate-900 px-3 md:px-4 py-1 md:py-1.5 rounded-lg border border-slate-700 text-xs md:text-base shadow-inner whitespace-nowrap">
                                        {Full_Game.full_total} runs
                                    </span>
                                </div>
                            </div>

                            {/* Odds Korumalı Alt/Üst Kıyaslama */}
                            {isOddsAvailable ? (
                                <div className="flex justify-between text-[11px] md:text-sm items-center bg-slate-900/50 p-2 md:p-3 rounded-lg border border-slate-700/50 mt-auto">
                                    <span className="text-gray-400 font-semibold leading-tight">Total Diff:</span>
                                    <span className={`font-black text-xs md:text-sm whitespace-nowrap ${Full_Game.full_total > Odds.over_under ? 'text-mlb-green' : 'text-blue-400'}`}>
                                        {Math.abs(Full_Game.full_total - Odds.over_under).toFixed(1)} {Full_Game.full_total > Odds.over_under ? 'OVER' : 'UNDER'} Book
                                    </span>
                                </div>
                            ) : (
                                <div className="flex justify-between text-[10px] items-center bg-slate-900/40 p-3 rounded-lg border border-slate-700/30 mt-auto text-gray-500 font-bold uppercase tracking-wider text-center">
                                    Book totals currently unavailable
                                </div>
                            )}
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
                                    {Weather.cbs_alert_word && Weather.cbs_alert_word !== "Clear" && (
                                        <div className={`mt-3 inline-block px-3 py-1 rounded text-[10px] font-black uppercase tracking-widest border ${Weather.red_flag_alert ? 'bg-red-900/30 text-red-400 border-red-500/50' : (Weather.cbs_alert_word.includes('Ideal') ? 'bg-green-900/30 text-green-400 border-green-500/50' : 'bg-amber-900/30 text-amber-400 border-amber-500/50')}`}>
                                            {Weather.red_flag_alert ? '🚩 ' : (Weather.cbs_alert_word.includes('Ideal') ? '✅ ' : '⚠️ ')}
                                            {Weather.cbs_alert_word}
                                        </div>
                                    )}
                                </>
                            ) : (
                                <span className="text-sm text-gray-500">Weather data unavailable</span>
                            )}
                        </div>

                        <div className="text-7xl opacity-[0.03] absolute right-4 top-1/2 -translate-y-1/2 md:relative md:opacity-10 md:transform-none mt-4 md:mt-0">
                            {Weather?.wind_mph > 10 ? '💨' : '🏟️'}
                        </div>
                    </div>

                    {/* AI MATCHUP INSIGHT (YENİ EKLENEN) */}
                    {aiInsight && (
                        <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-xl p-4 md:p-5 border border-blue-500/20 md:col-span-2 shadow-[0_0_15px_rgba(59,130,246,0.05)] relative overflow-hidden flex flex-col justify-center">
                            <div className="absolute top-0 left-0 w-1 h-full bg-blue-500/50"></div>
                            <div className="flex items-center gap-2 mb-3">
                                <span className="text-blue-400 text-lg leading-none">🧠</span>
                                <h3 className="text-[10px] md:text-xs text-blue-400 font-black uppercase tracking-widest pt-0.5">AI Matchup Insight</h3>
                            </div>
                            <div className="text-xs md:text-sm text-gray-300 leading-relaxed font-medium whitespace-pre-wrap">
                                {aiInsight}
                            </div>
                        </div>
                    )}

                </div>
            </div>

        </div>
    );
};

// Re-render optimizasyonu
const arePropsEqual = (prevProps, nextProps) => {
    return (
        prevProps.prediction.matchup?.status === nextProps.prediction.matchup?.status &&
        prevProps.prediction.matchup?.game_time === nextProps.prediction.matchup?.game_time &&
        JSON.stringify(prevProps.prediction.Odds) === JSON.stringify(nextProps.prediction.Odds) &&
        JSON.stringify(prevProps.prediction.Details) === JSON.stringify(nextProps.prediction.Details) &&
        JSON.stringify(prevProps.prediction.Weather) === JSON.stringify(nextProps.prediction.Weather) &&
        JSON.stringify(prevProps.prediction.NRFI) === JSON.stringify(nextProps.prediction.NRFI)
    );
};

export default React.memo(MatchupCard, arePropsEqual);