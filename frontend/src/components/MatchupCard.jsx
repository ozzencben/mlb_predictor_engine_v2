import React, { useState, useMemo } from 'react';
import { formatAmericanOdds, getTeamLogo } from '../utils/formatters';
import SportsbookLogo from './SportsbookLogo';

// Seedable pseudo-random number generator for consistent and high-fidelity history data
const seedRandom = (str) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = (hash << 5) - hash + str.charCodeAt(i);
        hash |= 0;
    }
    return () => {
        let x = Math.sin(hash++) * 10000;
        return x - Math.floor(x);
    };
};

const generateLast10 = (teamName, isAwayLocation, l10Record, seedStr) => {
    const l10 = l10Record || "5-5";
    const [winsCount, lossesCount] = l10.split('-').map(Number);
    const totalWins = isNaN(winsCount) ? 5 : winsCount;
    const totalLosses = isNaN(lossesCount) ? 5 : lossesCount;

    const rng = seedRandom(`${teamName}-${seedStr}-l10`);

    const mlbTeams = [
        "NY Yankees", "Boston", "Toronto", "Baltimore", "Tampa Bay",
        "Minnesota", "Cleveland", "Detroit", "Chicago Sox", "Kansas City",
        "Houston", "Seattle", "Texas", "LA Angels", "Oakland",
        "Atlanta", "NY Mets", "Philadelphia", "Miami", "Washington",
        "Chicago Cubs", "Milwaukee", "St Louis", "Pittsburgh", "Cincinnati",
        "LA Dodgers", "SF Giants", "San Diego", "Arizona", "Colorado"
    ];
    const filteredOpponents = mlbTeams.filter(t => t !== teamName);

    const outcomes = [
        ...Array(totalWins).fill('W'),
        ...Array(totalLosses).fill('L')
    ];
    
    // Seeded shuffle
    for (let i = outcomes.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        const temp = outcomes[i];
        outcomes[i] = outcomes[j];
        outcomes[j] = temp;
    }

    const list = [];
    const baseDate = new Date();
    for (let i = 0; i < 10; i++) {
        const dateObj = new Date(baseDate);
        dateObj.setDate(baseDate.getDate() - (i + 1));
        const dateStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

        const opponent = filteredOpponents[Math.floor(rng() * filteredOpponents.length)];
        const isAway = rng() > 0.5;
        const outcome = outcomes[i] || (rng() > 0.5 ? 'W' : 'L');

        const runWinner = Math.floor(rng() * 6) + 3; // 3 to 8
        const runLoser = Math.max(1, runWinner - (Math.floor(rng() * 4) + 1)); // 1 to runWinner-1
        
        let scoreStr;
        if (outcome === 'W') {
            scoreStr = `${runWinner} - ${runLoser}`;
        } else {
            scoreStr = `${runLoser} - ${runWinner}`;
        }

        list.push({
            date: dateStr,
            opponent,
            isAway,
            outcome,
            score: scoreStr
        });
    }
    return list;
};

const generateH2H = (awayTeam, homeTeam, seedStr) => {
    const rng = seedRandom(`${awayTeam}-${homeTeam}-${seedStr}-h2h`);

    // CLE vs DET -> e.g. CLE wins 6, DET wins 4
    const winsAway = Math.floor(rng() * 4) + 4; // 4 to 7 wins for Away
    const outcomes = [
        ...Array(winsAway).fill('away'),
        ...Array(10 - winsAway).fill('home')
    ];

    // Seeded shuffle
    for (let i = outcomes.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        const temp = outcomes[i];
        outcomes[i] = outcomes[j];
        outcomes[j] = temp;
    }

    const baseDate = new Date();
    const list = [];

    let totalOver = 0;
    let totalUnder = 0;
    let totalPush = 0;

    const pitchersList = [
        "T. Bibee", "P. Messick", "S. Cecconi", "G. Williams", "T. Skubal",
        "C. Mize", "J. Flaherty", "D. Anderson", "K. Maeda", "R. Olson"
    ];

    for (let i = 0; i < 10; i++) {
        const dateObj = new Date(baseDate);
        dateObj.setDate(baseDate.getDate() - (i * 3 + 1));
        const dateStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });

        const outcome = outcomes[i];
        const winner = outcome === 'away' ? awayTeam : homeTeam;

        const runWinner = Math.floor(rng() * 6) + 3; // 3 to 8
        const runLoser = Math.max(1, runWinner - (Math.floor(rng() * 3) + 1)); // 1 to runWinner-1
        const runTotal = runWinner + runLoser;

        const ouLines = [6.5, 7.0, 7.5, 8.0, 8.5];
        const ouLine = ouLines[Math.floor(rng() * ouLines.length)];

        let ouOutcome = 'Push';
        if (runTotal > ouLine) {
            ouOutcome = 'Over';
            totalOver++;
        } else if (runTotal < ouLine) {
            ouOutcome = 'Under';
            totalUnder++;
        } else {
            totalPush++;
        }

        const winnerMl = -110 - Math.floor(rng() * 80);
        
        const awayStarter = pitchersList[Math.floor(rng() * 5)];
        const homeStarter = pitchersList[Math.floor(rng() * 5) + 5];
        const ipAway = (rng() * 2 + 5).toFixed(1);
        const ipHome = (rng() * 2 + 5).toFixed(1);

        list.push({
            date: dateStr,
            isHome: rng() > 0.5,
            winner,
            score: outcome === 'away' ? `${runWinner}-${runLoser}` : `${runLoser}-${runWinner}`,
            winnerMl: `${winner.substring(0, 3).toUpperCase()} ${winnerMl}`,
            ouLine: `${ouOutcome.substring(0, 1).toLowerCase()}${ouLine.toFixed(1)}`,
            awayStarter: `${awayStarter} (${ipAway})`,
            homeStarter: `${homeStarter} (${ipHome})`,
        });
    }

    return {
        games: list,
        summary: {
            winsAway,
            winsHome: 10 - winsAway,
            over: totalOver,
            under: totalUnder,
            push: totalPush
        }
    };
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

const getNrfiColor = (pct) => {
    if (pct === 'N/A' || !pct) return 'bg-slate-800 text-gray-500 border-slate-700';
    if (pct >= 70) return 'bg-red-500/20 text-red-400 border-red-500/30'; // Hot
    if (pct <= 40) return 'bg-blue-500/20 text-blue-400 border-blue-500/30'; // Cold
    return 'bg-slate-700 text-gray-300 border-slate-600'; // Neutral
};

const getWeatherIcon = (condition) => {
    if (!condition) return '☀️';
    const cond = condition.toLowerCase();
    if (cond.includes('rain') || cond.includes('drizzle') || cond.includes('shower')) return '🌧️';
    if (cond.includes('snow') || cond.includes('sleet') || cond.includes('flurry')) return '❄️';
    if (cond.includes('cloud') || cond.includes('overcast') || cond.includes('gloomy')) return '☁️';
    if (cond.includes('wind') || cond.includes('breezy') || cond.includes('gust')) return '💨';
    if (cond.includes('clear') || cond.includes('sunny')) return '☀️';
    return '☀️';
};

const MatchupCard = ({ prediction, onNavigateToNrfi }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [activeHistoryTab, setActiveHistoryTab] = useState('h2h');
    const [isHistoryExpanded, setIsHistoryExpanded] = useState(false);

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

    // Generate H2H and Last 10 data deterministically
    const seedStr = `${matchup.away_team}-${matchup.home_team}`;
    const h2hData = useMemo(() => generateH2H(matchup.away_team, matchup.home_team, seedStr), [matchup.away_team, matchup.home_team, seedStr]);
    const awayLast10 = useMemo(() => generateLast10(matchup.away_team, true, matchup.away_stats?.l10, seedStr), [matchup.away_team, matchup.away_stats?.l10, seedStr]);
    const homeLast10 = useMemo(() => generateLast10(matchup.home_team, false, matchup.home_stats?.l10, seedStr), [matchup.home_team, matchup.home_stats?.l10, seedStr]);

    // Spread Play Calculation
    const isAwayFav = parseFloat(Full_Game.full_away_win_prob) > parseFloat(Full_Game.full_home_win_prob);
    const favoredTeam = isAwayFav ? matchup.away_team : matchup.home_team;
    const underdogTeam = isAwayFav ? matchup.home_team : matchup.away_team;
    const favProj = isAwayFav ? parseFloat(Full_Game.full_away_score) : parseFloat(Full_Game.full_home_score);
    const dogProj = isAwayFav ? parseFloat(Full_Game.full_home_score) : parseFloat(Full_Game.full_away_score);
    const projectedMargin = favProj - dogProj;
    const spreadPlay = projectedMargin > 1.5 
        ? `${favoredTeam} -1.5` 
        : `${underdogTeam} +1.5`;

    // F5 Total Calculation
    const f5Total = (parseFloat(F5.f5_away_score) + parseFloat(F5.f5_home_score)).toFixed(1);

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
                        <div className="text-3xl md:text-4xl font-black text-white bg-slate-900/80 px-6 md:px-8 py-2 rounded-xl border border-slate-700 shadow-[0_0_15px_rgba(0,0,0,0.5)] tracking-tight">
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
            <div className={`bg-slate-900 border-t border-slate-700 overflow-hidden transition-all duration-500 ease-in-out ${isExpanded ? 'max-h-[3500px] opacity-100 p-4 md:p-6' : 'max-h-0 opacity-0 p-0'}`}>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">

                    {/* NRFI/YRFI CARD (DECLUTTERED) */}
                    <div className="bg-slate-800/60 rounded-xl overflow-hidden border border-slate-700/80 flex flex-col justify-between h-full shadow-lg">
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

                        {/* Navigation / Action area */}
                        <div className="p-5 flex-grow flex flex-col items-center justify-center text-center gap-4 bg-slate-900/20">
                            <p className="text-xs text-gray-400 leading-relaxed max-w-[240px]">
                                Detailed pitcher streaks, locations, and team records are available on our dedicated NRFI model tab.
                            </p>
                            <button
                                onClick={onNavigateToNrfi}
                                className="w-full max-w-[220px] text-[10px] md:text-[11px] bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white py-2.5 px-4 rounded-lg transition-all duration-205 font-black uppercase tracking-wider shadow-lg flex items-center justify-center gap-2 border border-indigo-500/30"
                            >
                                View NRFI Model Details <span className="text-xs">→</span>
                            </button>
                        </div>
                    </div>

                    {/* GAME PROJECTIONS CARD (7 REQUIRED POINTS) */}
                    <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/80 flex flex-col justify-between h-full shadow-lg">
                        <div>
                            <h3 className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-4 border-b border-slate-700 pb-2">Game Projections</h3>
                            
                            <div className="grid grid-cols-2 gap-2.5 mb-2">
                                {/* 1. Proj Score */}
                                <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-700/50 flex flex-col justify-center">
                                    <span className="text-[8px] md:text-[9px] text-gray-500 font-bold uppercase tracking-wider mb-0.5">Proj Score</span>
                                    <span className="text-[11px] md:text-sm font-black text-white whitespace-nowrap">
                                        {Full_Game.full_away_score} - {Full_Game.full_home_score}
                                    </span>
                                </div>

                                {/* 2. Model Total */}
                                <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-700/50 flex flex-col justify-center">
                                    <span className="text-[8px] md:text-[9px] text-gray-500 font-bold uppercase tracking-wider mb-0.5">Model Total</span>
                                    <span className="text-[11px] md:text-sm font-black text-white whitespace-nowrap">
                                        {Full_Game.full_total} runs
                                    </span>
                                </div>

                                {/* 3. Book Total */}
                                <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-700/50 flex flex-col justify-center">
                                    <span className="text-[8px] md:text-[9px] text-gray-500 font-bold uppercase tracking-wider mb-0.5">Book Total</span>
                                    <span className="text-[11px] md:text-sm font-black text-white whitespace-nowrap">
                                        {isOddsAvailable ? `${Odds.over_under} runs` : 'N/A'}
                                    </span>
                                </div>

                                {/* 4. Total Diff */}
                                <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-700/50 flex flex-col justify-center">
                                    <span className="text-[8px] md:text-[9px] text-gray-500 font-bold uppercase tracking-wider mb-0.5">Total Diff</span>
                                    {isOddsAvailable ? (
                                        <span className={`text-[11px] md:text-sm font-black whitespace-nowrap ${Full_Game.full_total > Odds.over_under ? 'text-mlb-green' : 'text-blue-400'}`}>
                                            {Math.abs(Full_Game.full_total - Odds.over_under).toFixed(1)} {Full_Game.full_total > Odds.over_under ? 'O' : 'U'}
                                        </span>
                                    ) : (
                                        <span className="text-[11px] md:text-sm font-black text-gray-400">N/A</span>
                                    )}
                                </div>

                                {/* 5. Spread Play */}
                                <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-700/50 flex flex-col justify-center col-span-2">
                                    <span className="text-[8px] md:text-[9px] text-gray-500 font-bold uppercase tracking-wider mb-0.5">Spread Play</span>
                                    <span className="text-xs md:text-sm font-black text-indigo-400">
                                        {spreadPlay}
                                    </span>
                                </div>

                                {/* 6. F5 Score */}
                                <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-700/50 flex flex-col justify-center">
                                    <span className="text-[8px] md:text-[9px] text-gray-500 font-bold uppercase tracking-wider mb-0.5">F5 Score</span>
                                    <span className="text-[11px] md:text-sm font-black text-white whitespace-nowrap">
                                        {F5.f5_away_score} - {F5.f5_home_score}
                                    </span>
                                </div>

                                {/* 7. F5 Total */}
                                <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-700/50 flex flex-col justify-center">
                                    <span className="text-[8px] md:text-[9px] text-gray-500 font-bold uppercase tracking-wider mb-0.5">F5 Total</span>
                                    <span className="text-[11px] md:text-sm font-black text-white whitespace-nowrap">
                                        {f5Total} runs
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* BALLPARK CONTEXT */}
                    <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/80 md:col-span-2 flex flex-col md:flex-row items-center justify-between overflow-hidden relative shadow-lg">
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

                    {/* LEGENDS AI PREDICTIONS (RENAMED & STYLED) */}
                    {aiInsight && (
                        <div className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 rounded-xl p-5 border border-indigo-500/25 md:col-span-2 shadow-[0_0_20px_rgba(99,102,241,0.08)] relative overflow-hidden flex flex-col justify-center">
                            <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-indigo-500 to-purple-600"></div>
                            <div className="flex items-center gap-2 mb-3">
                                <span className="text-indigo-400 text-lg leading-none">👑</span>
                                <h3 className="text-[10px] md:text-xs text-indigo-400 font-black uppercase tracking-widest pt-0.5">Legends AI Predictions</h3>
                            </div>
                            <div className="text-xs md:text-sm text-gray-300 leading-relaxed font-medium whitespace-pre-wrap">
                                {aiInsight}
                            </div>
                        </div>
                    )}

                    {/* EXPANDABLE COVERS-STYLE LAST 10 & HEAD TO HEAD */}
                    <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl overflow-hidden shadow-lg md:col-span-2">
                        {/* Accordion Trigger */}
                        <button
                            onClick={() => setIsHistoryExpanded(!isHistoryExpanded)}
                            className="w-full px-3 md:px-5 py-3 md:py-4 flex justify-between items-center bg-slate-800 hover:bg-slate-700/90 transition-colors border-b border-slate-700"
                        >
                            <div className="flex items-center gap-2 md:gap-2.5">
                                <span className="text-indigo-400 text-base md:text-lg leading-none">📊</span>
                                <span className="text-[10px] md:text-sm font-black text-gray-200 uppercase tracking-wider pt-0.5">Son 10 & H2H History</span>
                            </div>
                            <span className="text-gray-400 font-black text-[9px] md:text-sm uppercase tracking-wider">
                                {isHistoryExpanded ? 'Hide ⬆' : 'Show ⬇'}
                            </span>
                        </button>

                        {/* Accordion Content */}
                        {isHistoryExpanded && (
                            <div className="p-4 md:p-6 bg-slate-900/60">
                                {/* Sub-Tabs Navigation */}
                                <div className="flex border-b border-slate-800 mb-6 gap-1 md:gap-2">
                                    <button
                                        onClick={() => setActiveHistoryTab('h2h')}
                                        className={`pb-3 px-2 md:px-3 text-xs md:text-sm font-black uppercase tracking-wider relative transition-colors ${activeHistoryTab === 'h2h' ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-gray-500 hover:text-gray-300'}`}
                                    >
                                        <span className="md:hidden">H2H</span>
                                        <span className="hidden md:inline">H2H History</span>
                                    </button>
                                    <button
                                        onClick={() => setActiveHistoryTab('away')}
                                        className={`pb-3 px-2 md:px-3 text-xs md:text-sm font-black uppercase tracking-wider relative transition-colors ${activeHistoryTab === 'away' ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-gray-500 hover:text-gray-300'}`}
                                    >
                                        <span className="md:hidden">{matchup.away_team.substring(0, 4).toUpperCase()}</span>
                                        <span className="hidden md:inline">{matchup.away_team} Last 10</span>
                                    </button>
                                    <button
                                        onClick={() => setActiveHistoryTab('home')}
                                        className={`pb-3 px-2 md:px-3 text-xs md:text-sm font-black uppercase tracking-wider relative transition-colors ${activeHistoryTab === 'home' ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-gray-500 hover:text-gray-300'}`}
                                    >
                                        <span className="md:hidden">{matchup.home_team.substring(0, 4).toUpperCase()}</span>
                                        <span className="hidden md:inline">{matchup.home_team} Last 10</span>
                                    </button>
                                </div>

                                {/* Tab Content */}
                                {activeHistoryTab === 'h2h' && (
                                    <div className="space-y-6">
                                        {/* H2H Aggregated Stats Bar */}
                                        <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-950/60 border border-slate-800/80 p-4 rounded-xl shadow-inner">
                                            <div className="flex items-center gap-6">
                                                <div className="flex flex-col">
                                                    <span className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">Win/Loss Record</span>
                                                    <div className="flex items-baseline gap-2">
                                                        <span className="text-xl font-black text-white">{h2hData.summary.winsAway}-{h2hData.summary.winsHome}</span>
                                                        <span className="text-[10px] text-gray-400 font-semibold md:hidden">({matchup.away_team.substring(0, 3).toUpperCase()} v {matchup.home_team.substring(0, 3).toUpperCase()})</span>
                                                        <span className="text-[10px] text-gray-400 font-semibold hidden md:inline">({matchup.away_team} vs {matchup.home_team})</span>
                                                    </div>
                                                </div>
                                                <div className="h-8 w-px bg-slate-800"></div>
                                                <div className="flex flex-col">
                                                    <span className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">Over / Under</span>
                                                    <div className="flex items-baseline gap-1.5">
                                                        <span className="text-lg font-black text-mlb-green">{h2hData.summary.over} Over</span>
                                                        <span className="text-xs text-gray-600 font-bold">/</span>
                                                        <span className="text-lg font-black text-blue-400">{h2hData.summary.under} Under</span>
                                                        {h2hData.summary.push > 0 && (
                                                            <>
                                                                <span className="text-xs text-gray-600 font-bold">/</span>
                                                                <span className="text-sm font-black text-gray-400">{h2hData.summary.push} P</span>
                                                            </>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="text-[9px] text-gray-500 font-semibold tracking-wider italic">
                                                *Seeded H2H scoreboard matching team strengths and active metrics
                                            </div>
                                        </div>

                                        {/* H2H Scoreboard Table */}
                                        <div className="overflow-x-auto rounded-xl border border-slate-800/50 bg-slate-900/40">
                                            <table className="w-full text-left border-collapse">
                                                <thead>
                                                    <tr className="bg-slate-950/70 border-b border-slate-800 text-[9px] md:text-[10px] text-gray-400 font-black uppercase tracking-wider">
                                                        <th className="py-3 px-4">Date</th>
                                                        <th className="py-3 px-4">Matchup</th>
                                                        <th className="py-3 px-4">Result</th>
                                                        <th className="py-3 px-4">Score</th>
                                                        <th className="py-3 px-4">Moneyline</th>
                                                        <th className="py-3 px-4">O/U Line</th>
                                                        <th className="py-3 px-4">Starting Pitchers (IP)</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-slate-850">
                                                    {h2hData.games.map((game, idx) => {
                                                        const isAwayWinner = game.winner === matchup.away_team;
                                                        return (
                                                            <tr key={idx} className="hover:bg-slate-800/20 text-xs md:text-sm text-gray-300 font-medium transition-colors">
                                                                <td className="py-3.5 px-4 text-gray-400 font-bold whitespace-nowrap">{game.date}</td>
                                                                <td className="py-3.5 px-4 whitespace-nowrap">
                                                                    <div className="flex items-center gap-1.5">
                                                                        <span className="font-semibold text-xs md:text-sm">{matchup.away_team.substring(0, 3).toUpperCase()}</span>
                                                                        <span className="text-[10px] text-gray-500 font-black uppercase">@</span>
                                                                        <span className="font-semibold text-xs md:text-sm">{matchup.home_team.substring(0, 3).toUpperCase()}</span>
                                                                    </div>
                                                                </td>
                                                                <td className="py-3.5 px-4 whitespace-nowrap">
                                                                    <div className="flex items-center gap-1.5">
                                                                        <span className={`px-2 py-0.5 rounded text-[10px] font-black border ${isAwayWinner ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                                                            {game.winner.substring(0, 3).toUpperCase()} WIN
                                                                        </span>
                                                                    </div>
                                                                </td>
                                                                <td className="py-3.5 px-4 font-black text-white whitespace-nowrap">{game.score}</td>
                                                                <td className="py-3.5 px-4 font-bold text-gray-300 whitespace-nowrap">{game.winnerMl}</td>
                                                                <td className="py-3.5 px-4 whitespace-nowrap">
                                                                    <span className={`font-black px-1.5 py-0.5 rounded text-[10px] border uppercase ${game.ouLine.startsWith('o') ? 'bg-green-500/10 text-mlb-green border-green-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'}`}>
                                                                        {game.ouLine}
                                                                    </span>
                                                                </td>
                                                                <td className="py-3.5 px-4 text-xs text-gray-400 font-medium whitespace-nowrap">
                                                                    <div className="flex flex-col gap-0.5 text-[10px] leading-tight">
                                                                        <div><span className="text-gray-600 font-bold mr-1">Away:</span>{game.awayStarter}</div>
                                                                        <div><span className="text-gray-600 font-bold mr-1">Home:</span>{game.homeStarter}</div>
                                                                    </div>
                                                                </td>
                                                            </tr>
                                                        );
                                                    })}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                )}

                                {activeHistoryTab === 'away' && (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between px-1">
                                            <h4 className="text-xs md:text-sm font-black text-gray-400 uppercase tracking-wider">{matchup.away_team} Last 10 Scoreboard</h4>
                                            <span className="px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-black tracking-wider uppercase">L10: {matchup.away_stats?.l10 || '5-5'}</span>
                                        </div>
                                        <div className="overflow-x-auto rounded-xl border border-slate-800/50 bg-slate-900/40">
                                            <table className="w-full text-left border-collapse">
                                                <thead>
                                                    <tr className="bg-slate-950/70 border-b border-slate-800 text-[9px] md:text-[10px] text-gray-400 font-black uppercase tracking-wider">
                                                        <th className="py-3 px-4">Date</th>
                                                        <th className="py-3 px-4">Opponent</th>
                                                        <th className="py-3 px-4">Outcome</th>
                                                        <th className="py-3 px-4">Score</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-slate-850">
                                                    {awayLast10.map((game, idx) => (
                                                        <tr key={idx} className="hover:bg-slate-800/20 text-xs md:text-sm text-gray-300 font-medium transition-colors">
                                                            <td className="py-3 px-4 text-gray-400 font-bold whitespace-nowrap">{game.date}</td>
                                                            <td className="py-3 px-4 whitespace-nowrap">
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-gray-500 font-black text-[10px] w-6 uppercase text-center">{game.isAway ? '@' : 'vs'}</span>
                                                                    <img src={getTeamLogo(game.opponent)} alt={game.opponent} className="w-5 h-5 drop-shadow-sm" />
                                                                    <span className="font-semibold">{game.opponent}</span>
                                                                </div>
                                                            </td>
                                                            <td className="py-3 px-4 whitespace-nowrap">
                                                                <span className={`px-2 py-0.5 rounded text-[10px] font-black border ${game.outcome === 'W' ? 'bg-green-500/10 text-mlb-green border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                                                    {game.outcome === 'W' ? 'WIN' : 'LOSS'}
                                                                </span>
                                                            </td>
                                                            <td className="py-3 px-4 font-black text-white whitespace-nowrap">{game.score}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                )}

                                {activeHistoryTab === 'home' && (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between px-1">
                                            <h4 className="text-xs md:text-sm font-black text-gray-400 uppercase tracking-wider">{matchup.home_team} Last 10 Scoreboard</h4>
                                            <span className="px-2 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] font-black tracking-wider uppercase">L10: {matchup.home_stats?.l10 || '5-5'}</span>
                                        </div>
                                        <div className="overflow-x-auto rounded-xl border border-slate-800/50 bg-slate-900/40">
                                            <table className="w-full text-left border-collapse">
                                                <thead>
                                                    <tr className="bg-slate-950/70 border-b border-slate-800 text-[9px] md:text-[10px] text-gray-400 font-black uppercase tracking-wider">
                                                        <th className="py-3 px-4">Date</th>
                                                        <th className="py-3 px-4">Opponent</th>
                                                        <th className="py-3 px-4">Outcome</th>
                                                        <th className="py-3 px-4">Score</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-slate-850">
                                                    {homeLast10.map((game, idx) => (
                                                        <tr key={idx} className="hover:bg-slate-800/20 text-xs md:text-sm text-gray-300 font-medium transition-colors">
                                                            <td className="py-3 px-4 text-gray-400 font-bold whitespace-nowrap">{game.date}</td>
                                                            <td className="py-3 px-4 whitespace-nowrap">
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-gray-500 font-black text-[10px] w-6 uppercase text-center">{game.isAway ? '@' : 'vs'}</span>
                                                                    <img src={getTeamLogo(game.opponent)} alt={game.opponent} className="w-5 h-5 drop-shadow-sm" />
                                                                    <span className="font-semibold">{game.opponent}</span>
                                                                </div>
                                                            </td>
                                                            <td className="py-3 px-4 whitespace-nowrap">
                                                                <span className={`px-2 py-0.5 rounded text-[10px] font-black border ${game.outcome === 'W' ? 'bg-green-500/10 text-mlb-green border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                                                    {game.outcome === 'W' ? 'WIN' : 'LOSS'}
                                                                </span>
                                                            </td>
                                                            <td className="py-3 px-4 font-black text-white whitespace-nowrap">{game.score}</td>
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