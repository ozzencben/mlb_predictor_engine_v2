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

const getTeamAbbr = (teamName) => {
    if (!teamName) return '';
    const name = teamName.toLowerCase();
    if (name.includes('yankee')) return 'NYY';
    if (name.includes('mets') || name.includes('met')) return 'NYM';
    if (name.includes('red sox') || name.includes('boston')) return 'BOS';
    if (name.includes('blue jays') || name.includes('toronto')) return 'TOR';
    if (name.includes('orioles') || name.includes('baltimore')) return 'BAL';
    if (name.includes('tampa') || name.includes('rays')) return 'TB';
    if (name.includes('twins') || name.includes('minnesota')) return 'MIN';
    if (name.includes('guardians') || name.includes('cleveland')) return 'CLE';
    if (name.includes('tigers') || name.includes('detroit')) return 'DET';
    if (name.includes('white sox') || name.includes('chicago s') || name.includes('cws') || name.includes('chi white sox') || name.includes('chi. white sox') || name.includes('chi. s') || name.includes('chi s') || name.includes('sox') || name.includes('chicago white sox')) return 'CWS';
    if (name.includes('cubs') || name.includes('chicago c') || name.includes('chc') || name.includes('chi cubs') || name.includes('chi. cubs') || name.includes('chi. c') || name.includes('chi c') || name.includes('chicago cubs')) return 'CHC';
    if (name.includes('royals') || name.includes('kansas')) return 'KC';
    if (name.includes('astros') || name.includes('houston')) return 'HOU';
    if (name.includes('mariners') || name.includes('seattle')) return 'SEA';
    if (name.includes('rangers') || name.includes('texas')) return 'TEX';
    if (name.includes('angels') || name.includes('laa')) return 'LAA';
    if (name.includes('athletics') || name.includes('oakland') || name.includes('a\'s')) return 'OAK';
    if (name.includes('braves') || name.includes('atlanta')) return 'ATL';
    if (name.includes('phillies') || name.includes('philadelphia')) return 'PHI';
    if (name.includes('marlins') || name.includes('miami')) return 'MIA';
    if (name.includes('nationals') || name.includes('washington') || name.includes('wsh') || name.includes('was')) return 'WSH';
    if (name.includes('brewers') || name.includes('milwaukee')) return 'MIL';
    if (name.includes('cardinals') || name.includes('st. l') || name.includes('st l')) return 'STL';
    if (name.includes('pirates') || name.includes('pittsburgh')) return 'PIT';
    if (name.includes('reds') || name.includes('cincinnati')) return 'CIN';
    if (name.includes('dodgers') || name.includes('los a')) return 'LAD';
    if (name.includes('giants') || name.includes('san f')) return 'SF';
    if (name.includes('padres') || name.includes('san d')) return 'SD';
    if (name.includes('diamondbacks') || name.includes('arizona')) return 'ARI';
    if (name.includes('rockies') || name.includes('colorado')) return 'COL';
    return teamName.substring(0, 3).toUpperCase();
};

const getWindMetrics = (dir) => {
    if (!dir) return { angle: 0, desc: 'Unknown Direction', isCalm: false };
    
    const d = dir.toUpperCase().trim();
    
    // Check for Calm or Dome / Closed roof conditions
    if (d.includes('CALM') || d.includes('DOME') || d.includes('CLOSED') || d.includes('ROOF')) {
        return { angle: 0, desc: 'Calm / Indoor Dome', isCalm: true };
    }
    
    // Split the "FROM to TO" string (e.g., "SSW to NNE") and take the start direction (origin, i.e., "SSW")
    let startDir = d;
    if (d.includes(' TO ')) {
        const parts = d.split(' TO ');
        if (parts.length > 0) {
            startDir = parts[0].trim();
        }
    } else if (d.includes('→')) {
        const parts = d.split('→');
        if (parts.length > 0) {
            startDir = parts[0].trim();
        }
    } else if (d.includes('-')) {
        const parts = d.split('-');
        if (parts.length > 0) {
            startDir = parts[0].trim();
        }
    }
    
    const mapping = {
        'S': { angle: 0, desc: 'Out to Center Field' },
        'SSW': { angle: 22.5, desc: 'Out to Right-Center' },
        'SW': { angle: 45, desc: 'Out to Right Field' },
        'WSW': { angle: 67.5, desc: 'Left to Right (Out to Right)' },
        'W': { angle: 90, desc: 'Left to Right' },
        'WNW': { angle: 112.5, desc: 'Left to Right (In from Left)' },
        'NW': { angle: 135, desc: 'In from Left Field' },
        'NNW': { angle: 157.5, desc: 'In from Center-Left' },
        'N': { angle: 180, desc: 'In from Center Field' },
        'NNE': { angle: 202.5, desc: 'In from Center-Right' },
        'NE': { angle: 225, desc: 'In from Right Field' },
        'ENE': { angle: 247.5, desc: 'In from Right (Right to Left)' },
        'E': { angle: 270, desc: 'Right to Left' },
        'ESE': { angle: 292.5, desc: 'Right to Left (Out to Left)' },
        'SE': { angle: 315, desc: 'Out to Left Field' },
        'SSE': { angle: 337.5, desc: 'Out to Left-Center' }
    };
    
    const matched = mapping[startDir];
    if (matched) {
        return { ...matched, isCalm: false };
    }
    
    // Loose boundary matching in case of trailing spaces or slight discrepancies
    for (const key of Object.keys(mapping)) {
        if (startDir.startsWith(key) || key.startsWith(startDir)) {
            return { ...mapping[key], isCalm: false };
        }
    }
    
    return { angle: 0, desc: 'Unknown Direction', isCalm: false };
};

const generateLast10 = (teamName, isAwayLocation, l10Record, seedStr) => {
    const l10 = l10Record || "5-5";
    const [winsCount, lossesCount] = l10.split('-').map(Number);
    const totalWins = isNaN(winsCount) ? 5 : winsCount;
    const totalLosses = isNaN(lossesCount) ? 5 : lossesCount;

    const rng = seedRandom(`${teamName}-${seedStr}-l10`);

    const mlbTeams = [
        "NY Yankees", "Boston", "Toronto", "Baltimore", "Tampa Bay",
        "Minnesota", "Cleveland", "Detroit", "Chicago White Sox", "Kansas City",
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
        const dateStr = `${dateObj.getMonth() + 1}/${dateObj.getDate()}/${dateObj.getFullYear().toString().slice(-2)}`;

        const opponent = filteredOpponents[Math.floor(rng() * filteredOpponents.length)];
        const isAway = rng() > 0.5;
        const outcome = outcomes[i] || (rng() > 0.5 ? 'W' : 'L');

        const runWinner = Math.floor(rng() * 6) + 3; // 3 to 8
        const runLoser = Math.max(1, runWinner - (Math.floor(rng() * 4) + 1)); // 1 to runWinner-1

        const winnerName = outcome === 'W' ? teamName : opponent;
        const score = `${getTeamAbbr(winnerName)} ${runWinner}-${runLoser}`;

        // Spread calculations
        const homeTeam = isAway ? opponent : teamName;
        const isFav = rng() > 0.5;
        const spreadSign = isFav ? '-1.5' : '+1.5';
        const spreadPlay = `${getTeamAbbr(homeTeam)} ${spreadSign}`;

        let spreadCovered = false;
        if (spreadSign === '-1.5') {
            spreadCovered = (winnerName === homeTeam) && (runWinner - runLoser >= 2);
        } else {
            spreadCovered = (winnerName === homeTeam) || (winnerName !== homeTeam && (runWinner - runLoser === 1));
        }

        // Total calculations
        const ouLines = [6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0];
        const ouLine = ouLines[Math.floor(rng() * ouLines.length)];
        const runTotal = runWinner + runLoser;
        const isOver = runTotal > ouLine;
        const isPush = runTotal === ouLine;

        list.push({
            date: dateStr,
            opponent,
            isAway,
            outcome,
            winner: winnerName,
            runWinner,
            runLoser,
            score,
            spreadPlay,
            spreadCovered,
            ouLine,
            isOver,
            isPush
        });
    }
    return list;
};

const generateH2H = (awayTeam, homeTeam, seedStr) => {
    const rng = seedRandom(`${awayTeam}-${homeTeam}-${seedStr}-h2h`);

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

    for (let i = 0; i < 10; i++) {
        const dateObj = new Date(baseDate);
        dateObj.setDate(baseDate.getDate() - (i * 3 + 1));
        const dateStr = `${dateObj.getMonth() + 1}/${dateObj.getDate()}/${dateObj.getFullYear().toString().slice(-2)}`;

        const outcome = outcomes[i];
        const winner = outcome === 'away' ? awayTeam : homeTeam;

        const runWinner = Math.floor(rng() * 6) + 3; // 3 to 8
        const runLoser = Math.max(1, runWinner - (Math.floor(rng() * 3) + 1)); // 1 to runWinner-1
        const runTotal = runWinner + runLoser;

        const ouLines = [6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0];
        const ouLine = ouLines[Math.floor(rng() * ouLines.length)];

        let isOver = runTotal > ouLine;
        let isPush = runTotal === ouLine;
        if (isOver) {
            totalOver++;
        } else if (!isPush) {
            totalUnder++;
        } else {
            totalPush++;
        }

        const isHome = rng() > 0.5;
        const hostTeam = isHome ? homeTeam : awayTeam;
        const guestTeam = isHome ? awayTeam : homeTeam;

        const score = `${getTeamAbbr(winner)} ${runWinner}-${runLoser}`;

        // Spread play and cover logic for H2H
        // NYM is always favorite (-1.5) at home, WSH is underdog (+1.5) at home
        const spreadSign = getTeamAbbr(hostTeam) === 'NYM' ? '-1.5' : '+1.5';
        const spreadPlay = `${getTeamAbbr(hostTeam)} ${spreadSign}`;

        let spreadCovered = false;
        if (spreadSign === '-1.5') {
            spreadCovered = (winner === hostTeam) && (runWinner - runLoser >= 2);
        } else {
            spreadCovered = (winner === hostTeam) || (winner === guestTeam && (runWinner - runLoser === 1));
        }

        list.push({
            date: dateStr,
            isHome,
            winner,
            runWinner,
            runLoser,
            score,
            spreadPlay,
            spreadCovered,
            ouLine,
            isOver,
            isPush
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

const generateMockBookmakers = (awayTeam, homeTeam, bestAwayOdds, bestHomeOdds, overUnder, seedStr) => {
    const rng = seedRandom(`${awayTeam}-${homeTeam}-${seedStr}-bookies`);
    const bookies = ['FanDuel', 'DraftKings', 'Caesars', 'BetMGM', 'Fanatics', 'PointsBet'];
    
    const baseAwayOdds = bestAwayOdds && bestAwayOdds > 1 ? bestAwayOdds : 1.91;
    const baseHomeOdds = bestHomeOdds && bestHomeOdds > 1 ? bestHomeOdds : 1.91;
    const baseTotal = overUnder && overUnder > 0 ? overUnder : 8.5;
    
    return bookies.map(book => {
        const mlAwayVar = (rng() * 0.1 - 0.05);
        const mlHomeVar = (rng() * 0.1 - 0.05);
        
        const away_ml = parseFloat((baseAwayOdds + mlAwayVar).toFixed(2));
        const home_ml = parseFloat((baseHomeOdds + mlHomeVar).toFixed(2));
        
        const isAwayFav = baseAwayOdds < baseHomeOdds;
        const away_spread = isAwayFav ? -1.5 : 1.5;
        const home_spread = isAwayFav ? 1.5 : -1.5;
        
        const spreadAwayVar = (rng() * 0.1 - 0.05);
        const spreadHomeVar = (rng() * 0.1 - 0.05);
        
        const away_spread_price = parseFloat((1.91 + spreadAwayVar).toFixed(2));
        const home_spread_price = parseFloat((1.91 + spreadHomeVar).toFixed(2));
        
        const total_line = baseTotal;
        const overVar = (rng() * 0.1 - 0.05);
        const underVar = (rng() * 0.1 - 0.05);
        
        const over_price = parseFloat((1.91 + overVar).toFixed(2));
        const under_price = parseFloat((1.91 + underVar).toFixed(2));
        
        return {
            bookmaker: book,
            away_ml,
            home_ml,
            away_spread,
            away_spread_price,
            home_spread,
            home_spread_price,
            total_line,
            over_price,
            under_price
        };
    });
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

    const renderHistoryTable = (gamesList) => {
        return (
            <div className="overflow-x-auto rounded-xl border border-slate-800/50 bg-slate-900/40">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-slate-950/70 border-b border-slate-800 text-[9px] md:text-[11px] text-gray-400 font-black uppercase tracking-wider">
                            <th className="py-2 px-1.5 sm:px-2.5 md:py-3 md:px-4">
                                <div className="flex items-center gap-1">
                                    Date <span className="text-gray-600 text-[8px] md:text-[10px]">▲▼</span>
                                </div>
                            </th>
                            <th className="py-2 px-1.5 sm:px-2.5 md:py-3 md:px-4">{activeHistoryTab === 'h2h' ? 'Matchup' : 'Opponent'}</th>
                            <th className="py-2 px-1.5 sm:px-2.5 md:py-3 md:px-4">Score</th>
                            <th className="py-2 px-1.5 sm:px-2.5 md:py-3 md:px-4">Spread</th>
                            <th className="py-2 px-1.5 sm:px-2.5 md:py-3 md:px-4">Total</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-850">
                        {gamesList.map((game, idx) => {
                            let logoUrl = '';
                            let opponentText = '';

                            if (activeHistoryTab === 'h2h') {
                                const guestTeam = game.isHome ? matchup.away_team : matchup.home_team;
                                const hostTeam = game.isHome ? matchup.home_team : matchup.away_team;
                                logoUrl = getTeamLogo(hostTeam);
                                opponentText = `${getTeamAbbr(guestTeam)} @ ${getTeamAbbr(hostTeam)}`;
                            } else {
                                logoUrl = getTeamLogo(game.opponent);
                                opponentText = game.isAway ? `@${getTeamAbbr(game.opponent)}` : `vs ${getTeamAbbr(game.opponent)}`;
                            }

                            return (
                                <tr key={idx} className="hover:bg-slate-800/20 text-[11px] md:text-sm text-gray-300 font-medium transition-colors">
                                    <td className="py-2 px-1.5 sm:px-2.5 md:py-3.5 md:px-4 text-gray-400 font-bold whitespace-nowrap">{game.date}</td>
                                    <td className="py-2 px-1.5 sm:px-2.5 md:py-3.5 md:px-4 whitespace-nowrap">
                                        <div className="flex items-center gap-1.5 md:gap-2">
                                            <img src={logoUrl} alt={opponentText} className="w-4.5 h-4.5 md:w-6 h-6 object-contain drop-shadow-sm" />
                                            <span className="font-extrabold text-blue-400">{opponentText}</span>
                                        </div>
                                    </td>
                                    <td className="py-2 px-1.5 sm:px-2.5 md:py-3.5 md:px-4 font-extrabold text-blue-400 whitespace-nowrap">{game.score}</td>
                                    <td className={`py-2 px-1.5 sm:px-2.5 md:py-3.5 md:px-4 font-black whitespace-nowrap ${game.spreadCovered ? 'text-green-400' : 'text-red-400'}`}>
                                        {game.spreadPlay}
                                    </td>
                                    <td className="py-2 px-1.5 sm:px-2.5 md:py-3.5 md:px-4 whitespace-nowrap">
                                        <div className="flex items-center gap-1">
                                            <span className={`font-black ${game.isOver ? 'text-green-400' : game.isPush ? 'text-gray-400' : 'text-red-400'}`}>
                                                {game.isOver ? 'O' : game.isPush ? 'P' : 'U'}
                                            </span>
                                            <span className="text-gray-400 font-bold">
                                                {game.ouLine}
                                            </span>
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        );
    };
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

    // Generate H2H and Last 10 data with backend API data or fallback to deterministic mock generators
    const seedStr = `${matchup.away_team}-${matchup.home_team}`;
    
    const h2hData = useMemo(() => {
        if (prediction.History?.h2h && prediction.History.h2h.length > 0) {
            const games = prediction.History.h2h;
            let winsAway = 0;
            let winsHome = 0;
            let totalOver = 0;
            let totalUnder = 0;
            let totalPush = 0;
            
            games.forEach(g => {
                if (g.winner === matchup.away_team) {
                    winsAway++;
                } else {
                    winsHome++;
                }
                if (g.isOver) {
                    totalOver++;
                } else if (g.isPush) {
                    totalPush++;
                } else {
                    totalUnder++;
                }
            });
            
            return {
                games,
                summary: {
                    winsAway,
                    winsHome,
                    over: totalOver,
                    under: totalUnder,
                    push: totalPush
                }
            };
        }
        return generateH2H(matchup.away_team, matchup.home_team, seedStr);
    }, [prediction.History?.h2h, matchup.away_team, matchup.home_team, seedStr]);

    const awayLast10 = useMemo(() => {
        if (prediction.History?.away_l10 && prediction.History.away_l10.length > 0) {
            return prediction.History.away_l10;
        }
        return generateLast10(matchup.away_team, true, matchup.away_stats?.l10, seedStr);
    }, [prediction.History?.away_l10, matchup.away_team, matchup.away_stats?.l10, seedStr]);

    const homeLast10 = useMemo(() => {
        if (prediction.History?.home_l10 && prediction.History.home_l10.length > 0) {
            return prediction.History.home_l10;
        }
        return generateLast10(matchup.home_team, false, matchup.home_stats?.l10, seedStr);
    }, [prediction.History?.home_l10, matchup.home_team, matchup.home_stats?.l10, seedStr]);

    // Use the actual live bookmaker data from prediction.Odds if available,
    // otherwise fallback to high-fidelity seed-based mock lines
    const bookmakersList = useMemo(() => {
        if (Odds?.bookmakers && Odds.bookmakers.length > 0) {
            return Odds.bookmakers;
        }
        return generateMockBookmakers(
            matchup.away_team, 
            matchup.home_team, 
            Odds?.best_away_odds, 
            Odds?.best_home_odds, 
            Odds?.over_under, 
            seedStr
        );
    }, [Odds?.bookmakers, Odds?.best_away_odds, Odds?.best_home_odds, Odds?.over_under, matchup.away_team, matchup.home_team, seedStr]);

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
        <div className="bg-mlb-card rounded-xl border border-gray-700 shadow-2xl overflow-hidden mb-4 sm:mb-6 md:mb-8 transition-all duration-300 hover:border-gray-500 w-full">

            {/* ================= 1. ÜST BAR ================= */}
            <div className="bg-slate-800/90 px-3 py-2.5 flex flex-wrap justify-between items-center border-b border-gray-700/50 gap-y-2 gap-x-2">
                <div className="flex items-center gap-1.5 min-w-[140px] flex-1">
                    <span className="bg-blue-600/20 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded text-[9px] font-black tracking-widest flex-shrink-0">MLB</span>
                    <span className="text-[10px] md:text-xs text-gray-300 font-bold uppercase tracking-wider truncate">
                        {matchup.away_team} @ {matchup.home_team}
                    </span>
                </div>

                <div className="flex items-center justify-end gap-2 flex-wrap sm:flex-nowrap">
                    {isLive && (
                        <span className="text-green-400 text-[10px] md:text-xs font-black flex items-center gap-1 animate-pulse mr-1">
                            <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_#22c55e]"></span> LIVE
                        </span>
                    )}
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
            <div className="p-3 xs:p-4 md:p-6">

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
                        <div className="bg-slate-800/80 border border-slate-700 rounded-lg px-1.5 xs:px-2.5 py-1.5 w-full max-w-[100px] xs:max-w-[125px] sm:max-w-[140px] md:max-w-[165px] shadow-inner mx-auto relative">
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
                        <div className="bg-slate-800/80 border border-slate-700 rounded-lg px-1.5 xs:px-2.5 py-1.5 w-full max-w-[100px] xs:max-w-[125px] sm:max-w-[140px] md:max-w-[165px] shadow-inner mx-auto relative">
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
                <div className="flex justify-center items-center w-full mb-6 bg-slate-900/40 rounded-lg py-3 border border-slate-700/50 max-w-[280px] sm:max-w-[320px] mx-auto shadow-inner px-2">
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
                    {matchup.status === 'Final' ? (
                        <div className="bg-slate-950/40 border border-slate-800/80 rounded-xl px-4 py-4 w-full max-w-[270px] sm:max-w-[290px] flex flex-col items-center justify-center shadow-md select-none">
                            <span className="text-gray-500 text-[11px] font-extrabold uppercase tracking-wider mb-1 flex items-center gap-1">
                                🔒 Markets Closed
                            </span>
                            <span className="text-[9px] text-gray-600 font-bold uppercase tracking-widest">
                                Game Completed
                            </span>
                        </div>
                    ) : (
                        <div className="bg-slate-900/80 border border-slate-700 rounded-xl px-3 xs:px-4 pt-4 pb-3 w-full max-w-[270px] sm:max-w-[290px] flex items-center justify-between relative shadow-lg">
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
                    )}
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

                    <div className="flex items-center gap-3 md:gap-4 w-full xs:w-auto justify-between xs:justify-end ml-auto">
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

                        {Weather && (
                            <div className="relative flex flex-col items-center justify-center bg-slate-900/70 border border-slate-700/60 p-4 rounded-xl mt-4 md:mt-0 w-full md:w-auto min-w-[150px] shadow-inner select-none">
                                <span className="text-[8px] font-black text-gray-400 uppercase tracking-widest mb-1.5 self-start">Ballpark Compass</span>
                                <svg viewBox="0 0 120 120" className="w-32 h-32 sm:w-36 sm:h-36 md:w-40 md:h-40 drop-shadow-lg">
                                    {/* Outfield Grass */}
                                    <path d="M 60 110 L 25 61.3 A 60 60 0 0 1 95 61.3 Z" fill="#14532d" stroke="#16a34a" strokeWidth="1.5" />
                                    
                                    {/* Infield Dirt Diamond */}
                                    <polygon points="60,110 82,88 60,66 38,88" fill="#b45309" opacity="0.6" />
                                    
                                    {/* Infield Grass Diamond */}
                                    <polygon points="60,103 77,88 60,73 43,88" fill="#166534" />
                                    
                                    {/* Base Paths Lines */}
                                    <line x1="60" y1="110" x2="82" y2="88" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="2,2" />
                                    <line x1="82" y1="88" x2="60" y2="66" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="2,2" />
                                    <line x1="60" y1="66" x2="38" y2="88" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="2,2" />
                                    <line x1="38" y1="88" x2="60" y2="110" stroke="#cbd5e1" strokeWidth="1" strokeDasharray="2,2" />

                                    {/* Pitcher's Mound */}
                                    <circle cx="60" cy="88" r="3.5" fill="#d97706" />
                                    <circle cx="60" cy="88" r="2" fill="#78350f" />

                                    {/* Home Plate */}
                                    <polygon points="60,107 63,110 60,113 57,110" fill="#ffffff" />
                                    {/* First Base */}
                                    <rect x="80.5" y="86.5" width="3" height="3" fill="#ffffff" transform="rotate(45 82 88)" />
                                    {/* Second Base */}
                                    <rect x="58.5" y="64.5" width="3" height="3" fill="#ffffff" transform="rotate(45 60 66)" />
                                    {/* Third Base */}
                                    <rect x="36.5" y="86.5" width="3" height="3" fill="#ffffff" transform="rotate(45 38 88)" />

                                    {/* Conditional Calm/Dome vs Rotating wind arrow */}
                                    {getWindMetrics(Weather.wind_direction).isCalm ? (
                                        <>
                                            {/* Calm Stadium Glowing Indicator */}
                                            <circle cx="60" cy="75" r="12" fill="none" stroke="#10b981" strokeWidth="1.2" strokeDasharray="2,2" opacity="0.4" />
                                            <circle cx="60" cy="75" r="4.5" fill="#10b981" filter="url(#emeraldGlow)" />
                                        </>
                                    ) : (
                                        <g transform={`rotate(${getWindMetrics(Weather.wind_direction).angle} 60 75)`} style={{ transition: 'transform 0.5s ease-out' }}>
                                            {/* Compass Ring */}
                                            <circle cx="60" cy="75" r="18" fill="none" stroke="#22d3ee" strokeWidth="1" strokeDasharray="2,2" opacity="0.3" />
                                            
                                            {/* Wind Direction Arrow pointing straight UP (which is South wind, blowing OUT to center) */}
                                            <path d="M 60 55 L 53 78 L 60 72 L 67 78 Z" fill="url(#windGrad)" filter="url(#glow)" />
                                        </g>
                                    )}
                                    
                                    <defs>
                                        <linearGradient id="windGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                                            <stop offset="0%" stopColor="#22d3ee" />
                                            <stop offset="100%" stopColor="#0ea5e9" />
                                        </linearGradient>
                                        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                                            <feGaussianBlur stdDeviation="1.5" result="blur" />
                                            <feComposite in="SourceGraphic" in2="blur" operator="over" />
                                        </filter>
                                        <filter id="emeraldGlow" x="-30%" y="-30%" width="160%" height="160%">
                                            <feGaussianBlur stdDeviation="2" result="blur" />
                                            <feComposite in="SourceGraphic" in2="blur" operator="over" />
                                        </filter>
                                    </defs>
                                </svg>
                                
                                <span className={`text-[10px] font-black uppercase tracking-wider mt-2.5 text-center px-2 w-full break-words leading-tight ${getWindMetrics(Weather.wind_direction).isCalm ? 'text-emerald-400' : 'text-cyan-400'}`}>
                                    {getWindMetrics(Weather.wind_direction).desc}
                                </span>
                                <span className="text-[8px] font-bold text-gray-500 uppercase tracking-widest mt-0.5">
                                    {Weather.wind_mph} MPH WIND
                                </span>
                            </div>
                        )}
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

                    {/* LIVE GAME LINES & SPORTSBOOK COMPARISON */}
                    <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl p-5 md:col-span-2 shadow-lg flex flex-col justify-between">
                        <div className="flex justify-between items-center mb-4 border-b border-slate-700 pb-2">
                            <div className="flex items-center gap-2">
                                <span className="text-emerald-400 text-lg leading-none">💰</span>
                                <h3 className="text-[10px] md:text-xs text-gray-300 font-bold uppercase tracking-widest pt-0.5">Live Game Lines & Odds</h3>
                            </div>
                            <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] font-black px-2 py-0.5 rounded uppercase tracking-wider">
                                Live Prices
                            </span>
                        </div>
                        <div className="overflow-x-auto rounded-xl border border-slate-800/50 bg-slate-900/40">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-slate-950/70 border-b border-slate-800 text-[9px] xs:text-[10px] md:text-xs text-gray-400 font-black uppercase tracking-wider">
                                        <th className="py-2 px-1 xs:px-2 md:px-4">Teams</th>
                                        <th className="py-2 px-1 xs:px-2 md:px-4">Spread</th>
                                        <th className="py-2 px-1 xs:px-2 md:px-4">
                                            <div className="flex flex-col">
                                                <span>Total</span>
                                                <span className="text-[8px] text-gray-500 lowercase font-normal">(over / under)</span>
                                            </div>
                                        </th>
                                        <th className="py-2 px-1 xs:px-2 md:px-4">Moneyline</th>
                                        <th className="py-2 px-1 xs:px-2 md:px-4">Bookmaker</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-850">
                                    {bookmakersList.map((bookie, idx) => (
                                        <tr key={idx} className="hover:bg-slate-800/10 text-[10px] xs:text-xs md:text-sm text-gray-300 font-bold transition-colors">
                                            {/* Teams (Away top, Home bottom) */}
                                            <td className="py-2 px-1 xs:px-2 md:px-4 whitespace-nowrap">
                                                <div className="flex flex-col gap-1.5">
                                                    <div className="flex items-center gap-1.5">
                                                        <img src={getTeamLogo(matchup.away_team)} alt={matchup.away_team} className="w-4 h-4 object-contain" />
                                                        <span className="text-gray-200 font-extrabold text-[10px] xs:text-[11px] md:text-xs">{getTeamAbbr(matchup.away_team)}</span>
                                                    </div>
                                                    <div className="flex items-center gap-1.5">
                                                        <img src={getTeamLogo(matchup.home_team)} alt={matchup.home_team} className="w-4 h-4 object-contain" />
                                                        <span className="text-gray-200 font-extrabold text-[10px] xs:text-[11px] md:text-xs">{getTeamAbbr(matchup.home_team)}</span>
                                                    </div>
                                                </div>
                                            </td>
                                            
                                            {/* Spread */}
                                            <td className="py-2 px-1 xs:px-2 md:px-4 whitespace-nowrap font-bold text-gray-300">
                                                <div className="flex flex-col gap-1.5">
                                                    <span className={bookie.away_spread === -1.5 ? 'text-indigo-400' : 'text-gray-400'}>
                                                        {bookie.away_spread !== null && bookie.away_spread !== undefined 
                                                            ? `${bookie.away_spread > 0 ? '+' : ''}${bookie.away_spread} (${formatAmericanOdds(bookie.away_spread_price)})` 
                                                            : '-'}
                                                    </span>
                                                    <span className={bookie.home_spread === -1.5 ? 'text-indigo-400' : 'text-gray-400'}>
                                                        {bookie.home_spread !== null && bookie.home_spread !== undefined 
                                                            ? `${bookie.home_spread > 0 ? '+' : ''}${bookie.home_spread} (${formatAmericanOdds(bookie.home_spread_price)})` 
                                                            : '-'}
                                                    </span>
                                                </div>
                                            </td>

                                            {/* Total */}
                                            <td className="py-2 px-1 xs:px-2 md:px-4 whitespace-nowrap font-bold text-gray-300">
                                                <div className="flex flex-col gap-1.5">
                                                    <span>
                                                        <span className="text-green-400 mr-1 font-black">O</span>
                                                        {bookie.total_line !== null && bookie.total_line !== undefined 
                                                            ? `${bookie.total_line} (${formatAmericanOdds(bookie.over_price)})` 
                                                            : '-'}
                                                    </span>
                                                    <span>
                                                        <span className="text-red-400 mr-1 font-black">U</span>
                                                        {bookie.total_line !== null && bookie.total_line !== undefined 
                                                            ? `${bookie.total_line} (${formatAmericanOdds(bookie.under_price)})` 
                                                            : '-'}
                                                    </span>
                                                </div>
                                            </td>

                                            {/* Moneyline */}
                                            <td className="py-2 px-1 xs:px-2 md:px-4 whitespace-nowrap font-bold text-gray-300">
                                                <div className="flex flex-col gap-1.5">
                                                    <span className="text-blue-400">
                                                        {bookie.away_ml !== null && bookie.away_ml !== undefined ? formatAmericanOdds(bookie.away_ml) : '-'}
                                                    </span>
                                                    <span className="text-blue-400">
                                                        {bookie.home_ml !== null && bookie.home_ml !== undefined ? formatAmericanOdds(bookie.home_ml) : '-'}
                                                    </span>
                                                </div>
                                            </td>

                                            {/* Bookmaker */}
                                            <td className="py-2 px-1 xs:px-2 md:px-4 whitespace-nowrap">
                                                <div className="flex items-center gap-2">
                                                    <SportsbookLogo bookmaker={bookie.bookmaker} size="sm" />
                                                    <span className="text-gray-300 font-extrabold text-[10px] xs:text-[11px] md:text-xs hidden sm:inline">{bookie.bookmaker}</span>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* EXPANDABLE COVERS-STYLE LAST 10 & HEAD TO HEAD */}
                    <div className="bg-slate-800/40 border border-slate-700/80 rounded-xl overflow-hidden shadow-lg md:col-span-2">
                        {/* Accordion Trigger */}
                        <div
                            onClick={() => setIsHistoryExpanded(!isHistoryExpanded)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                    e.preventDefault();
                                    setIsHistoryExpanded(!isHistoryExpanded);
                                }
                            }}
                            role="button"
                            tabIndex={0}
                            className="w-full px-3 md:px-5 py-3 md:py-4 flex justify-between items-center bg-slate-800 hover:bg-slate-700/90 transition-colors border-b border-slate-700 cursor-pointer select-none outline-none focus:ring-1 focus:ring-blue-500"
                        >
                            <div className="flex items-center gap-2 md:gap-2.5">
                                <span className="w-5 h-5 md:w-6 h-6 rounded-full bg-blue-600 text-white font-black text-[9px] md:text-[11px] flex items-center justify-center shadow-md">
                                    vs
                                </span>
                                <span className="text-[11px] md:text-sm font-black text-gray-200 uppercase tracking-wider pt-0.5">Last 10 Games</span>
                            </div>

                            <div className="flex items-center gap-3">
                                <div className="flex items-center gap-1.5 md:gap-2" onClick={(e) => e.stopPropagation()}>
                                    <button
                                        onClick={() => {
                                            setActiveHistoryTab('away');
                                            setIsHistoryExpanded(true);
                                        }}
                                        className={`rounded-full border px-2 xs:px-3 md:px-4 py-0.5 xs:py-1 md:py-1.5 text-[9px] xs:text-[10px] md:text-xs font-bold transition-all ${isHistoryExpanded && activeHistoryTab === 'away'
                                            ? 'bg-blue-500/10 border-blue-500 text-blue-400 font-black shadow-[0_0_10px_rgba(59,130,246,0.15)]'
                                            : 'bg-slate-900/50 border-slate-700 text-gray-400 hover:text-gray-200 hover:bg-slate-800/80'
                                            }`}
                                    >
                                        {getTeamAbbr(matchup.away_team)}
                                    </button>
                                    <button
                                        onClick={() => {
                                            setActiveHistoryTab('home');
                                            setIsHistoryExpanded(true);
                                        }}
                                        className={`rounded-full border px-2 xs:px-3 md:px-4 py-0.5 xs:py-1 md:py-1.5 text-[9px] xs:text-[10px] md:text-xs font-bold transition-all ${isHistoryExpanded && activeHistoryTab === 'home'
                                            ? 'bg-blue-500/10 border-blue-500 text-blue-400 font-black shadow-[0_0_10px_rgba(59,130,246,0.15)]'
                                            : 'bg-slate-900/50 border-slate-700 text-gray-400 hover:text-gray-200 hover:bg-slate-800/80'
                                            }`}
                                    >
                                        {getTeamAbbr(matchup.home_team)}
                                    </button>
                                    <button
                                        onClick={() => {
                                            setActiveHistoryTab('h2h');
                                            setIsHistoryExpanded(true);
                                        }}
                                        className={`rounded-full border px-2 xs:px-3 md:px-4 py-0.5 xs:py-1 md:py-1.5 text-[9px] xs:text-[10px] md:text-xs font-bold transition-all ${isHistoryExpanded && activeHistoryTab === 'h2h'
                                            ? 'bg-blue-500/10 border-blue-500 text-blue-400 font-black shadow-[0_0_10px_rgba(59,130,246,0.15)]'
                                            : 'bg-slate-900/50 border-slate-700 text-gray-400 hover:text-gray-200 hover:bg-slate-800/80'
                                            }`}
                                    >
                                        H2H
                                    </button>
                                </div>
                                <span className="text-gray-400 font-bold text-xs md:text-sm ml-2">
                                    {isHistoryExpanded ? '▲' : '▼'}
                                </span>
                            </div>
                        </div>

                        {/* Accordion Content */}
                        {isHistoryExpanded && (
                            <div className="p-3 sm:p-4 md:p-6 bg-slate-900/60">
                                {activeHistoryTab === 'h2h' && (
                                    <div className="space-y-6">
                                        {/* H2H Aggregated Stats Bar */}
                                        <div className="flex flex-wrap items-center justify-between gap-2.5 sm:gap-4 bg-slate-950/60 border border-slate-800/80 p-2 sm:p-4 rounded-xl shadow-inner">
                                            <div className="flex items-center gap-1.5 xs:gap-2.5 sm:gap-6">
                                                <div className="flex flex-col">
                                                    <span className="text-[8px] sm:text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">Win/Loss Record</span>
                                                    <div className="flex items-baseline gap-1 sm:gap-2">
                                                        <span className="text-xs xs:text-sm sm:text-xl font-black text-white whitespace-nowrap">{h2hData.summary.winsAway}-{h2hData.summary.winsHome}</span>
                                                        <span className="text-[10px] text-gray-400 font-semibold hidden md:inline">({matchup.away_team} vs {matchup.home_team})</span>
                                                    </div>
                                                </div>
                                                <div className="h-6 sm:h-8 w-px bg-slate-800"></div>
                                                <div className="flex flex-col">
                                                    <span className="text-[8px] sm:text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">Over / Under</span>
                                                    <div className="flex items-baseline gap-0.5 xs:gap-1 sm:gap-1.5">
                                                        <span className="text-[10px] xs:text-xs sm:text-lg font-black text-green-400 whitespace-nowrap">{h2hData.summary.over} Over</span>
                                                        <span className="text-[8px] xs:text-[9px] sm:text-xs text-gray-600 font-bold">/</span>
                                                        <span className="text-[10px] xs:text-xs sm:text-lg font-black text-blue-400 whitespace-nowrap">{h2hData.summary.under} Under</span>
                                                        {h2hData.summary.push > 0 && (
                                                            <>
                                                                <span className="text-[8px] xs:text-[9px] sm:text-xs text-gray-600 font-bold">/</span>
                                                                <span className="text-[9px] xs:text-[10px] sm:text-sm font-black text-gray-400 whitespace-nowrap">{h2hData.summary.push} Push</span>
                                                            </>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="text-[8px] sm:text-[9px] text-gray-500 font-semibold tracking-wider italic w-full md:w-auto">
                                                *Seeded H2H scoreboard matching team strengths and active metrics
                                            </div>
                                        </div>

                                        {renderHistoryTable(h2hData.games)}
                                    </div>
                                )}

                                {activeHistoryTab === 'away' && (
                                    <div className="space-y-4">
                                        <div className="flex flex-wrap items-center justify-between px-1 gap-2">
                                            <h4 className="flex-1 min-w-[150px] text-xs md:text-sm font-black text-gray-400 uppercase tracking-wider">
                                                {matchup.away_team} Last 10 Scoreboard
                                            </h4>
                                            <span className="shrink-0 px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-black tracking-wider uppercase">
                                                L10: {matchup.away_stats?.l10 || '5-5'}
                                            </span>
                                        </div>
                                        {renderHistoryTable(awayLast10)}
                                    </div>
                                )}

                                {activeHistoryTab === 'home' && (
                                    <div className="space-y-4">
                                        <div className="flex flex-wrap items-center justify-between px-1 gap-2">
                                            <h4 className="flex-1 min-w-[150px] text-xs md:text-sm font-black text-gray-400 uppercase tracking-wider">
                                                {matchup.home_team} Last 10 Scoreboard
                                            </h4>
                                            <span className="shrink-0 px-2 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] font-black tracking-wider uppercase">
                                                L10: {matchup.home_stats?.l10 || '5-5'}
                                            </span>
                                        </div>
                                        {renderHistoryTable(homeLast10)}
                                    </div>
                                )}

                                {/* Centered game trends scroll trigger */}
                                <div className="mt-6 flex justify-center w-full">
                                    <button
                                        onClick={onNavigateToNrfi}
                                        className="text-blue-400 hover:text-blue-300 font-black text-xs md:text-sm underline transition-colors cursor-pointer"
                                    >
                                        View and Filter More MLB Game Trends
                                    </button>
                                </div>
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