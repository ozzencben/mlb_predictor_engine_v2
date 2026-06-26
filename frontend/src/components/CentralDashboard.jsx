import React, { useMemo } from 'react';
import { getTeamAbbr } from '../utils/formatters';
import { SPORTS_CONFIG } from '../utils/sports_config';
import apiClient from '../api/client';

function CentralDashboard({
    setActiveSport,
    predictions = [],
    tennisPredictions = null,
    wnbaPayload = null,
    dailyEdges = null,
    loading = false,
    systemDate = '',
    yesterdayMlbPredictions = [],
    yesterdayTennisResults = [],
    yesterdayWnbaResults = []
}) {
    const [standingsData, setStandingsData] = React.useState(null);
    const [standingsLoading, setStandingsLoading] = React.useState(true);
    const [rankingsData, setRankingsData] = React.useState(null);
    const [rankingsLoading, setRankingsLoading] = React.useState(true);

    React.useEffect(() => {
        let isMounted = true;
        
        const fetchStandings = async () => {
            try {
                const res = await fetch("https://statsapi.mlb.com/api/v1/standings?leagueId=103,104");
                const data = await res.json();
                if (isMounted) {
                    setStandingsData(data);
                    setStandingsLoading(false);
                }
            } catch (err) {
                console.warn("Failed to fetch MLB standings from StatsAPI:", err.message);
                if (isMounted) {
                    setStandingsLoading(false);
                }
            }
        };

        const fetchTennisRankings = async () => {
            try {
                const res = await apiClient.get("/tennis/rankings");
                if (isMounted) {
                    setRankingsData(res.data);
                    setRankingsLoading(false);
                }
            } catch (err) {
                console.warn("Failed to fetch Tennis Rankings:", err.message);
                if (isMounted) {
                    setRankingsLoading(false);
                }
            }
        };

        fetchStandings();
        fetchTennisRankings();

        return () => {
            isMounted = false;
        };
    }, []);

    const wnbaGames = wnbaPayload?.predictions || [];
    const wnbaMeta = wnbaPayload?.model_meta || {};
    const activeTennisList = tennisPredictions?.active_predictions || [];

    const wnbaTopPlay = useMemo(() => {
        let best = null;
        let bestEdge = -1;
        wnbaGames.forEach(game => {
            (game.alt_bets || []).forEach(bet => {
                const edge = parseFloat(bet.edge || 0);
                if (edge > bestEdge) {
                    bestEdge = edge;
                    best = { game, bet };
                }
            });
        });
        return best;
    }, [wnbaGames]);

    const liveEngineStats = useMemo(() => ({
        mlb: predictions?.length || 0,
        tennis: activeTennisList.length,
        wnba: wnbaGames.length,
    }), [predictions, activeTennisList, wnbaGames]);

    const alEastTeams = useMemo(() => {
        if (!standingsData) return null;
        const alEastRecord = standingsData.records?.find(r => r.division?.id === 201);
        if (!alEastRecord) return null;
        return alEastRecord.teamRecords?.map(tr => {
            const lastTen = tr.records?.splitRecords?.find(sr => sr.type === 'lastTen');
            return {
                name: tr.team.name,
                wins: tr.wins,
                losses: tr.losses,
                gb: tr.gamesBack || '—',
                l10: lastTen ? `${lastTen.wins}-${lastTen.losses}` : '0-0'
            };
        });
    }, [standingsData]);

    const nlWestTeams = useMemo(() => {
        if (!standingsData) return null;
        const nlWestRecord = standingsData.records?.find(r => r.division?.id === 203);
        if (!nlWestRecord) return null;
        return nlWestRecord.teamRecords?.map(tr => {
            const lastTen = tr.records?.splitRecords?.find(sr => sr.type === 'lastTen');
            return {
                name: tr.team.name,
                wins: tr.wins,
                losses: tr.losses,
                gb: tr.gamesBack || '—',
                l10: lastTen ? `${lastTen.wins}-${lastTen.losses}` : '0-0'
            };
        });
    }, [standingsData]);

    const alEast = alEastTeams;
    const nlWest = nlWestTeams;

    // Yesterday's scoreboard ribbon mapping
    const yesterdayScores = useMemo(() => {
        const mlbItems = yesterdayMlbPredictions
            .filter(p => p.result)
            .map(p => {
                const isAway = p.Full_Game?.full_away_win_prob > 0.50;
                const predictionTeam = isAway ? p.matchup.away_team : p.matchup.home_team;
                const edgeValue = isAway ? p.Odds?.away_edge_pct : p.Odds?.home_edge_pct;
                return {
                    sport: 'mlb',
                    icon: '⚾',
                    away: p.matchup.away_team,
                    home: p.matchup.home_team,
                    awayScore: p.result.away_actual_score,
                    homeScore: p.result.home_actual_score,
                    status: 'FINAL',
                    prediction: `${getTeamAbbr(predictionTeam)} ML`,
                    edge: edgeValue ? `+${parseFloat(edgeValue).toFixed(1)}%` : '',
                    success: p.result.ml_correct
                };
            });

        const tennisItems = yesterdayTennisResults.map(r => {
            const predWinnerName = r.predicted_winner === 1 ? r.home_player : r.away_player;
            const predictionLabel = `${predWinnerName.split(' ').pop() || predWinnerName} ML`;
            const homeSets = r.actual_winner === 1 ? 2 : 0;
            const awaySets = r.actual_winner === 2 ? 2 : 0;
            return {
                sport: 'tennis',
                icon: '🎾',
                away: r.away_player,
                home: r.home_player,
                awayScore: awaySets,
                homeScore: homeSets,
                status: 'FINAL (SETS)',
                prediction: predictionLabel,
                edge: r.edge_percentage ? `+${parseFloat(r.edge_percentage).toFixed(1)}%` : '',
                success: r.is_correct
            };
        });

        const wnbaItems = yesterdayWnbaResults.map(r => {
            const scores = r.actual_score ? r.actual_score.split('-').map(Number) : [0, 0];
            const awayScore = scores[0] || 0;
            const homeScore = scores[1] || 0;
            return {
                sport: 'wnba',
                icon: '🏀',
                away: r.away_team_abbr,
                home: r.home_team_abbr,
                awayScore,
                homeScore,
                status: 'FINAL',
                prediction: `${r.predicted_winner_abbr} ML`,
                edge: r.home_win_prob ? `${Math.round(r.home_win_prob * 100)}% Win` : '',
                success: r.ml_correct
            };
        });

        return [...mlbItems, ...tennisItems, ...wnbaItems];
    }, [yesterdayMlbPredictions, yesterdayTennisResults, yesterdayWnbaResults]);

    // Dynamic Spotlight Pick calculations based on maximum Edge (MLB or Tennis)
    const spotlightPick = useMemo(() => {
        let bestEdge = -1;
        let bestPick = null;

        // MLB
        if (predictions && predictions.length > 0) {
            predictions.forEach(p => {
                const awayEdge = parseFloat(p.Odds?.away_edge_pct || 0);
                const homeEdge = parseFloat(p.Odds?.home_edge_pct || 0);
                const maxMlEdge = Math.max(awayEdge, homeEdge);

                if (maxMlEdge > bestEdge) {
                    bestEdge = maxMlEdge;
                    const isAway = awayEdge >= homeEdge;
                    bestPick = {
                        sport: '⚾ MLB',
                        sportId: 'mlb',
                        matchup: `${getTeamAbbr(p.matchup.away_team)} @ ${getTeamAbbr(p.matchup.home_team)}`,
                        type: 'MONEYLINE',
                        selection: isAway ? `${getTeamAbbr(p.matchup.away_team)} ML` : `${getTeamAbbr(p.matchup.home_team)} ML`,
                        edge: `${maxMlEdge.toFixed(1)}%`,
                        odds: isAway ? (p.Odds.away_odds > 0 ? `+${p.Odds.away_odds}` : p.Odds.away_odds) : (p.Odds.home_odds > 0 ? `+${p.Odds.home_odds}` : p.Odds.home_odds),
                        confidence: isAway ? `${(p.Full_Game?.full_away_win_prob * 100).toFixed(0)}%` : `${(p.Full_Game?.full_home_win_prob * 100).toFixed(0)}%`,
                        book: 'Best Odds'
                    };
                }
            });
        }

        // Tennis
        if (activeTennisList.length > 0) {
            activeTennisList.forEach(t => {
                const edge = parseFloat(t.edge_percentage || 0);
                if (edge > bestEdge) {
                    bestEdge = edge;
                    const isHome = t.home_win_probability > t.away_win_probability;
                    const selectionName = isHome ? t.home_player : t.away_player;
                    const confidenceVal = isHome ? t.home_win_probability : t.away_win_probability;
                    const oddsVal = isHome ? t.p1_odds : t.p2_odds;

                    bestPick = {
                        sport: '🎾 TENNIS',
                        sportId: 'tennis',
                        matchup: `${t.home_player} vs ${t.away_player}`,
                        type: 'MONEYLINE',
                        selection: `${selectionName.split(' ').pop() || selectionName} ML`,
                        edge: edge != null && !isNaN(edge) ? `${edge.toFixed(1)}%` : '—',
                        odds: oddsVal ? (oddsVal >= 2.0 ? `+${Math.round((oddsVal - 1.0) * 100)}` : `${Math.round(-100.0 / (oddsVal - 1.0))}`) : 'Best Odds',
                        confidence: confidenceVal != null && !isNaN(confidenceVal) ? `${confidenceVal.toFixed(0)}%` : '—',
                        book: 'Best Odds'
                    };
                }
            });
        }

        // WNBA
        wnbaGames.forEach(game => {
            (game.alt_bets || []).forEach(bet => {
                const edge = parseFloat(bet.edge || 0);
                if (edge > bestEdge) {
                    bestEdge = edge;
                    const oddsVal = bet.odds;
                    const americanOdds = oddsVal != null
                        ? (parseInt(oddsVal, 10) > 0 ? `+${oddsVal}` : `${oddsVal}`)
                        : 'Best Odds';
                    bestPick = {
                        sport: '🏀 WNBA',
                        sportId: 'wnba',
                        matchup: `${game.away_team_abbr} @ ${game.home_team_abbr}`,
                        type: (bet.market || 'PICK').toUpperCase(),
                        selection: bet.pick,
                        edge: `${edge.toFixed(1)}%`,
                        odds: americanOdds,
                        confidence: game.home_win_prob >= 0.5
                            ? `${(game.home_win_prob * 100).toFixed(0)}% ${game.home_team_abbr}`
                            : `${(game.away_win_prob * 100).toFixed(0)}% ${game.away_team_abbr}`,
                        book: 'Best Odds'
                    };
                }
            });
        });

        return bestPick;
    }, [predictions, tennisPredictions, wnbaGames]);

    // Top 3 value picks for each active sport
    const topValuePicks = useMemo(() => {
        const mlbPicks = [];
        const tennisPicks = [];

        // MLB Edge calculation
        if (predictions && predictions.length > 0) {
            predictions.forEach(p => {
                const awayEdge = parseFloat(p.Odds?.away_edge_pct || 0);
                const homeEdge = parseFloat(p.Odds?.home_edge_pct || 0);
                
                if (awayEdge > 0 || homeEdge > 0) {
                    const isAway = awayEdge >= homeEdge;
                    const maxEdge = isAway ? awayEdge : homeEdge;
                    const selectionTeam = isAway ? p.matchup.away_team : p.matchup.home_team;
                    const oddsVal = isAway ? p.Odds.away_odds : p.Odds.home_odds;
                    const confidenceVal = isAway ? p.Full_Game?.full_away_win_prob : p.Full_Game?.full_home_win_prob;

                    mlbPicks.push({
                        sport: 'mlb',
                        icon: '⚾',
                        matchup: `${getTeamAbbr(p.matchup.away_team)} @ ${getTeamAbbr(p.matchup.home_team)}`,
                        selection: `${getTeamAbbr(selectionTeam)} ML`,
                        edge: maxEdge,
                        odds: oddsVal > 0 ? `+${oddsVal}` : oddsVal,
                        confidence: `${(confidenceVal * 100).toFixed(0)}%`
                    });
                }
            });
        }

        // Tennis Edge calculation
        if (activeTennisList.length > 0) {
            activeTennisList.forEach(t => {
                const edge = parseFloat(t.edge_percentage || 0);
                if (edge > 0) {
                    const isHome = t.home_win_probability > t.away_win_probability;
                    const selectionName = isHome ? t.home_player : t.away_player;
                    const confidenceVal = isHome ? t.home_win_probability : t.away_win_probability;
                    const oddsVal = isHome ? t.p1_odds : t.p2_odds;

                    let americanOdds = 'Best Odds';
                    if (oddsVal) {
                        americanOdds = oddsVal >= 2.0 
                            ? `+${Math.round((oddsVal - 1.0) * 100)}` 
                            : `${Math.round(-100.0 / (oddsVal - 1.0))}`;
                    }

                    tennisPicks.push({
                        sport: 'tennis',
                        icon: '🎾',
                        matchup: `${t.home_player} vs ${t.away_player}`,
                        selection: `${selectionName.split(' ').pop() || selectionName} ML`,
                        edge: edge,
                        odds: americanOdds,
                        confidence: `${confidenceVal.toFixed(0)}%`
                    });
                }
            });
        }

        // WNBA Edge calculation
        const wnbaPicks = [];
        wnbaGames.forEach(game => {
            (game.alt_bets || []).forEach(bet => {
                const edge = parseFloat(bet.edge || 0);
                if (edge > 0) {
                    const oddsVal = bet.odds;
                    const americanOdds = oddsVal != null
                        ? (parseInt(oddsVal, 10) > 0 ? `+${oddsVal}` : `${oddsVal}`)
                        : '—';
                    wnbaPicks.push({
                        sport: 'wnba',
                        icon: '🏀',
                        matchup: `${game.away_team_abbr} @ ${game.home_team_abbr}`,
                        selection: bet.pick,
                        edge,
                        odds: americanOdds,
                        confidence: game.predicted_winner_abbr
                            ? `${game.predicted_winner_abbr} ML`
                            : '—',
                    });
                }
            });
        });

        const topMlb = mlbPicks.sort((a, b) => b.edge - a.edge).slice(0, 3);
        const topTennis = tennisPicks.sort((a, b) => b.edge - a.edge).slice(0, 3);
        const topWnba = wnbaPicks.sort((a, b) => b.edge - a.edge).slice(0, 3);

        return {
            mlb: topMlb,
            tennis: topTennis,
            wnba: topWnba,
        };
    }, [predictions, tennisPredictions, wnbaGames]);

    return (
        <div className="space-y-10 animate-fade-in pb-12">

            {/* ================= LIVE ENGINES RIBBON ================= */}
            <div className="w-full bg-slate-900/40 border border-slate-850 rounded-2xl p-3 md:p-4 backdrop-blur-md">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div className="flex flex-wrap items-center gap-2 md:gap-3">
                        <span className="text-[9px] font-black text-slate-500 uppercase tracking-[0.2em] mr-1">Live Engines</span>
                        {[
                            { id: 'mlb', icon: '⚾', label: 'MLB', count: liveEngineStats.mlb, status: 'LIVE', color: 'emerald' },
                            { id: 'tennis', icon: '🎾', label: 'Tennis', count: liveEngineStats.tennis, status: 'LIVE', color: 'emerald' },
                            { id: 'wnba', icon: '🏀', label: 'WNBA', count: liveEngineStats.wnba, status: 'BETA', color: 'cyan' },
                        ].map(engine => (
                            <button
                                key={engine.id}
                                onClick={() => setActiveSport(engine.id)}
                                className={`flex items-center gap-2 px-3 py-2 rounded-xl border transition-all cursor-pointer hover:scale-[1.02]
                                    ${engine.id === 'wnba'
                                        ? 'bg-orange-950/20 border-orange-500/25 hover:border-orange-400/40'
                                        : 'bg-slate-950/50 border-slate-900 hover:border-slate-800'
                                    }`}
                            >
                                <span className="relative flex h-2 w-2">
                                    <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${engine.color === 'cyan' ? 'bg-cyan-400' : 'bg-emerald-400'}`} />
                                    <span className={`relative inline-flex rounded-full h-2 w-2 ${engine.color === 'cyan' ? 'bg-cyan-500' : 'bg-emerald-500'}`} />
                                </span>
                                <span className="text-[10px] font-black text-white uppercase tracking-wider">
                                    {engine.icon} {engine.label}
                                </span>
                                <span className={`text-[8px] font-black uppercase px-1.5 py-0.5 rounded border
                                    ${engine.status === 'BETA'
                                        ? 'text-cyan-400 bg-cyan-950/50 border-cyan-500/30'
                                        : 'text-emerald-400 bg-emerald-950/50 border-emerald-500/30'
                                    }`}>
                                    {engine.status}
                                </span>
                                <span className="text-[9px] text-slate-400 font-bold">
                                    {engine.count} game{engine.count !== 1 ? 's' : ''}
                                </span>
                            </button>
                        ))}
                    </div>

                    {wnbaGames.length > 0 && (
                        <div className="flex items-center gap-2 overflow-x-auto pb-1">
                            <span className="text-[8px] font-black text-slate-600 uppercase tracking-widest flex-shrink-0">WNBA Today</span>
                            {wnbaGames.map(game => (
                                <button
                                    key={game.game_id}
                                    onClick={() => setActiveSport('wnba')}
                                    className="flex-shrink-0 flex items-center gap-2 bg-slate-950/60 border border-slate-900 hover:border-orange-500/30 rounded-xl px-3 py-2 transition-all cursor-pointer"
                                >
                                    {game.away_logo && (
                                        <img src={game.away_logo} alt="" className="w-5 h-5 object-contain" />
                                    )}
                                    <span className="text-[9px] font-black text-slate-500">@</span>
                                    {game.home_logo && (
                                        <img src={game.home_logo} alt="" className="w-5 h-5 object-contain" />
                                    )}
                                    <span className="text-[9px] font-black text-white">
                                        {game.predicted_winner_abbr} {(Math.max(game.home_win_prob, game.away_win_prob) * 100).toFixed(0)}%
                                    </span>
                                    {game.bet_count > 0 && (
                                        <span className="text-[7px] font-black text-emerald-400 bg-emerald-950/40 border border-emerald-500/20 px-1 py-0.5 rounded">
                                            {game.bet_count} play{game.bet_count !== 1 ? 's' : ''}
                                        </span>
                                    )}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* ================= BLOK 2: YESTERDAY'S SCOREBOARD RIBBON ================= */}
            <div className="w-full">
                <div className="flex flex-col sm:flex-row items-center sm:items-center justify-between mb-3 px-1 gap-2">
                    <span className="text-[10px] md:text-xs font-black text-slate-500 uppercase tracking-[0.2em] flex items-center gap-1.5">
                        <span>📊</span> Yesterday's Results & Verification
                    </span>
                    <span className="text-[9px] text-emerald-400 font-extrabold uppercase tracking-widest bg-emerald-950/40 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                        verified results
                    </span>
                </div>

                {/* Horizontal Scroll Scoreboard Ribbon or Empty State */}
                {yesterdayScores.length === 0 ? (
                    <div className="w-full bg-slate-900/20 border border-slate-850 rounded-2xl p-6 text-center select-none backdrop-blur-md">
                        <span className="text-xl block mb-2">📅</span>
                        <span className="text-xs font-extrabold text-slate-400 uppercase tracking-widest block">No predictions completed yesterday</span>
                        <p className="text-[10px] text-slate-500 font-bold mt-1">Check back later once today's active games are finalized.</p>
                    </div>
                ) : (
                    <div className="-mx-4 sm:mx-0">
                        <div className="flex flex-row overflow-x-auto gap-4 pb-3 pt-1 px-4 sm:px-1 scroll-smooth snap-x snap-mandatory scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
                            {yesterdayScores.map((score, idx) => (
                                <div
                                    key={idx}
                                    className="flex-shrink-0 w-[240px] sm:w-[260px] bg-slate-900/40 border border-slate-850 rounded-2xl p-4 flex flex-col justify-between snap-start hover:border-slate-800 transition-all duration-300 relative overflow-hidden group shadow-lg shadow-black/20"
                                >
                                    <div className={`absolute top-0 left-0 right-0 h-[2px] ${score.success ? 'bg-gradient-to-r from-emerald-500/80 to-teal-500/80' : 'bg-gradient-to-r from-rose-500/80 to-orange-500/80'}`} />

                                    <div className="flex justify-between items-center mb-3">
                                        <span className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                                            <span>{score.icon}</span>
                                            <span>{score.sport.toUpperCase()}</span>
                                        </span>
                                        <span className="text-[9px] text-slate-500 font-bold tracking-tight">
                                            {score.status}
                                        </span>
                                    </div>

                                    <div className="space-y-1.5 my-1">
                                        <div className="flex justify-between items-center">
                                            <span className="text-xs font-bold text-gray-300 truncate max-w-[150px]">
                                                {getTeamAbbr(score.away)}
                                            </span>
                                            <span className={`text-sm font-black ${score.awayScore > score.homeScore ? 'text-white' : 'text-slate-500'}`}>
                                                {score.awayScore}
                                            </span>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-xs font-bold text-gray-300 truncate max-w-[150px]">
                                                {getTeamAbbr(score.home)}
                                            </span>
                                            <span className={`text-sm font-black ${score.homeScore > score.awayScore ? 'text-white' : 'text-slate-500'}`}>
                                                {score.homeScore}
                                            </span>
                                        </div>
                                    </div>

                                    <div className="mt-3 pt-2 border-t border-slate-950 flex justify-between items-center">
                                        <span className="text-[10px] text-slate-500 font-bold">
                                            Pick: <strong className="text-slate-300">{score.prediction}</strong>
                                        </span>
                                        <span className={`text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md flex items-center gap-1 ${score.success
                                                ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-500/25'
                                                : 'bg-rose-950/60 text-rose-400 border border-rose-500/25'
                                            }`}>
                                            {score.success ? `✅ Hit ${score.edge}` : '❌ Lose'}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* ================= BLOK 1: SPOTLIGHT BANNER ================= */}
            {spotlightPick ? (
                <div className="w-full relative rounded-3xl overflow-hidden border border-indigo-500/20 bg-slate-900/20 backdrop-blur-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] border-t border-t-indigo-500/30 group">
                    <div className="absolute top-0 right-0 w-[300px] h-[300px] bg-indigo-500/10 rounded-full blur-[100px] pointer-events-none animate-pulse duration-[10s]"></div>
                    <div className="absolute bottom-0 left-0 w-[200px] h-[200px] bg-cyan-500/5 rounded-full blur-[80px] pointer-events-none"></div>

                    <div className="p-6 md:p-8 flex flex-col md:flex-row items-center justify-between gap-6 relative z-10">
                        <div className="space-y-4 text-center md:text-left w-full md:w-2/3">
                            <div className="flex flex-wrap items-center justify-center md:justify-start gap-2.5">
                                <span className="text-[9px] font-black uppercase tracking-[0.2em] bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 px-3 py-1 rounded-full animate-pulse">
                                    ⚡ Spotlight Edge of the Day
                                </span>
                                <span className="text-[9px] font-black uppercase tracking-[0.2em] bg-cyan-500/10 border border-cyan-500/25 text-cyan-300 px-3 py-1 rounded-full">
                                    {spotlightPick.sport}
                                </span>
                            </div>

                            <div className="space-y-2">
                                <h3 className="text-xl md:text-3xl font-black text-white tracking-tight">
                                    {spotlightPick.matchup}
                                </h3>
                                <p className="text-xs sm:text-sm text-slate-400 font-semibold leading-relaxed">
                                    Our model detected the highest mathematical advantage (<span className="text-indigo-400 font-black">Edge</span>) for this matchup today compared to market odds.
                                </p>
                            </div>

                            <div className="grid grid-cols-3 gap-3 bg-slate-950/60 border border-slate-900 rounded-2xl p-4 max-w-md mx-auto md:mx-0 shadow-inner">
                                <div className="text-center border-r border-slate-900">
                                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Selection</span>
                                    <span className="text-xs font-black text-white mt-1 block truncate">{spotlightPick.selection}</span>
                                </div>
                                <div className="text-center border-r border-slate-900">
                                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Odds (Book)</span>
                                    <span className="text-xs font-black text-cyan-400 mt-1 block">{spotlightPick.odds}</span>
                                </div>
                                <div className="text-center">
                                    <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Model Win %</span>
                                    <span className="text-xs font-black text-indigo-400 mt-1 block">{spotlightPick.confidence}</span>
                                </div>
                            </div>
                        </div>

                        <div className="w-full md:w-1/3 flex flex-col items-center justify-center text-center p-4 bg-slate-950/40 border border-slate-900/60 rounded-2xl shadow-inner md:min-h-[180px]">
                            <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest block mb-1">
                                VALUE ADVANTAGE
                            </span>
                            <div className="text-4xl md:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-indigo-400 to-purple-400 tracking-tighter filter drop-shadow-[0_0_20px_rgba(99,102,241,0.3)] animate-pulse">
                                {spotlightPick.edge}
                            </div>
                            <span className="text-[10px] text-indigo-400 font-extrabold uppercase tracking-widest mt-1">
                                MATHEMATICAL EDGE
                            </span>

                            <button
                                onClick={() => setActiveSport(spotlightPick.sportId || 'mlb')}
                                className="mt-5 w-full bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white text-[10px] sm:text-xs font-black uppercase tracking-widest py-3 rounded-xl transition-all duration-300 shadow-md shadow-indigo-500/15 hover:scale-[1.02] active:scale-[0.98] cursor-pointer flex items-center justify-center gap-1.5"
                            >
                                View Predictions Screen <span>→</span>
                            </button>
                        </div>
                    </div>
                </div>
            ) : null}

            {/* ================= BLOK 4: TOP DAILY VALUE PICKS ================= */}
            <div className="space-y-4">
                <div className="flex flex-col sm:flex-row items-center justify-between mb-2 px-1 gap-2">
                    <span className="text-[10px] md:text-xs font-black text-slate-500 uppercase tracking-[0.2em] flex items-center gap-1.5">
                        <span>🔥</span> Top daily value picks
                    </span>
                    <span className="text-[9px] text-indigo-400 font-extrabold uppercase tracking-widest bg-indigo-950/40 border border-indigo-500/20 px-2 py-0.5 rounded-full">
                        highest edge projections
                    </span>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* MLB Value Picks */}
                    <div className="bg-slate-900/10 border border-slate-900/60 rounded-3xl p-6 space-y-4 relative overflow-hidden backdrop-blur-md">
                        <div className="flex justify-between items-center pb-3 border-b border-slate-950">
                            <span className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">
                                <span>⚾</span> MLB Top Value
                            </span>
                            <span className="text-[9px] text-slate-500 font-bold">Max 3 Picks</span>
                        </div>

                        {topValuePicks.mlb.length === 0 ? (
                            <div className="py-10 text-center text-slate-500 text-xs font-semibold">
                                No value picks identified for MLB today.
                            </div>
                        ) : (
                            <div className="space-y-3.5">
                                {topValuePicks.mlb.map((pick, idx) => (
                                    <div
                                        key={idx}
                                        className="bg-slate-950/40 border border-slate-900 hover:border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 transition-all"
                                    >
                                        <div className="space-y-1">
                                            <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">
                                                Matchup
                                            </span>
                                            <h6 className="text-xs font-extrabold text-white">
                                                {pick.matchup}
                                            </h6>
                                        </div>

                                        <div className="grid grid-cols-3 gap-3 bg-slate-900/30 border border-slate-900/60 rounded-xl p-2.5 w-full sm:w-auto">
                                            <div className="text-center px-2">
                                                <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider block">Selection</span>
                                                <span className="text-[10px] font-black text-white truncate max-w-[80px] block mt-0.5">{pick.selection}</span>
                                            </div>
                                            <div className="text-center px-2 border-x border-slate-900/60">
                                                <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider block">Odds</span>
                                                <span className="text-[10px] font-black text-cyan-400 block mt-0.5">{pick.odds}</span>
                                            </div>
                                            <div className="text-center px-2">
                                                <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider block">Edge</span>
                                                <span className="text-[10px] font-black text-emerald-400 block mt-0.5">+{pick.edge.toFixed(1)}%</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Tennis Value Picks */}
                    <div className="bg-slate-900/10 border border-slate-900/60 rounded-3xl p-6 space-y-4 relative overflow-hidden backdrop-blur-md">
                        <div className="flex justify-between items-center pb-3 border-b border-slate-950">
                            <span className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">
                                <span>🎾</span> Tennis Top Value
                            </span>
                            <span className="text-[9px] text-slate-500 font-bold">Max 3 Picks</span>
                        </div>

                        {topValuePicks.tennis.length === 0 ? (
                            <div className="py-10 text-center text-slate-500 text-xs font-semibold">
                                No value picks identified for Tennis today.
                            </div>
                        ) : (
                            <div className="space-y-3.5">
                                {topValuePicks.tennis.map((pick, idx) => (
                                    <div
                                        key={idx}
                                        className="bg-slate-950/40 border border-slate-900 hover:border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 transition-all"
                                    >
                                        <div className="space-y-1">
                                            <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">
                                                Matchup
                                            </span>
                                            <h6 className="text-xs font-extrabold text-white truncate max-w-[180px]">
                                                {pick.matchup}
                                            </h6>
                                        </div>

                                        <div className="grid grid-cols-3 gap-3 bg-slate-900/30 border border-slate-900/60 rounded-xl p-2.5 w-full sm:w-auto">
                                            <div className="text-center px-2">
                                                <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider block">Selection</span>
                                                <span className="text-[10px] font-black text-white truncate max-w-[80px] block mt-0.5">{pick.selection}</span>
                                            </div>
                                            <div className="text-center px-2 border-x border-slate-900/60">
                                                <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider block">Odds</span>
                                                <span className="text-[10px] font-black text-cyan-400 block mt-0.5">{pick.odds}</span>
                                            </div>
                                            <div className="text-center px-2">
                                                <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider block">Edge</span>
                                                <span className="text-[10px] font-black text-emerald-400 block mt-0.5">+{pick.edge.toFixed(1)}%</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* WNBA Value Picks */}
                    <div className="bg-slate-900/10 border border-orange-500/15 rounded-3xl p-6 space-y-4 relative overflow-hidden backdrop-blur-md">
                        <div className="flex justify-between items-center pb-3 border-b border-slate-950">
                            <span className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">
                                <span>🏀</span> WNBA Top Value
                            </span>
                            <span className="text-[8px] font-black text-cyan-400 bg-cyan-950/50 border border-cyan-500/30 px-1.5 py-0.5 rounded uppercase">Beta</span>
                        </div>

                        {topValuePicks.wnba.length === 0 ? (
                            <div className="py-10 text-center text-slate-500 text-xs font-semibold">
                                No value picks identified for WNBA today.
                            </div>
                        ) : (
                            <div className="space-y-3.5">
                                {topValuePicks.wnba.map((pick, idx) => (
                                    <div
                                        key={idx}
                                        className="bg-slate-950/40 border border-slate-900 hover:border-orange-500/20 rounded-2xl p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 transition-all"
                                    >
                                        <div className="space-y-1">
                                            <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">
                                                Matchup
                                            </span>
                                            <h6 className="text-xs font-extrabold text-white">
                                                {pick.matchup}
                                            </h6>
                                        </div>

                                        <div className="grid grid-cols-3 gap-3 bg-slate-900/30 border border-slate-900/60 rounded-xl p-2.5 w-full sm:w-auto">
                                            <div className="text-center px-2">
                                                <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider block">Selection</span>
                                                <span className="text-[10px] font-black text-white truncate max-w-[80px] block mt-0.5">{pick.selection}</span>
                                            </div>
                                            <div className="text-center px-2 border-x border-slate-900/60">
                                                <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider block">Odds</span>
                                                <span className="text-[10px] font-black text-cyan-400 block mt-0.5">{pick.odds}</span>
                                            </div>
                                            <div className="text-center px-2">
                                                <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider block">Edge</span>
                                                <span className="text-[10px] font-black text-emerald-400 block mt-0.5">+{pick.edge.toFixed(1)}%</span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        <button
                            onClick={() => setActiveSport('wnba')}
                            className="w-full text-[9px] font-black uppercase tracking-widest text-orange-400 hover:text-orange-300 py-2 border border-orange-500/20 rounded-xl hover:bg-orange-950/20 transition-all cursor-pointer"
                        >
                            Open WNBA Dashboard →
                        </button>
                    </div>
                </div>
            </div>

            {/* ================= BLOK 3: ACTIVE SPORTS DASHBOARD ================= */}
            <div className="space-y-4">
                <span className="text-[10px] md:text-xs font-black text-slate-500 uppercase tracking-[0.2em] px-1 block text-center sm:text-left">
                    ⚡ Available Sports Predictors
                </span>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <div
                        onClick={() => setActiveSport('mlb')}
                        className="group bg-slate-900/30 border border-slate-850 rounded-3xl p-6 hover:border-blue-500/30 hover:shadow-[0_10px_30px_rgba(59,130,246,0.1)] transition-all duration-300 cursor-pointer flex flex-col justify-between gap-6 relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-full blur-xl group-hover:bg-blue-500/10 transition-colors pointer-events-none"></div>
                        <div className="flex justify-between items-start">
                            <span className="text-3xl leading-none">⚾</span>
                            <span className="text-[8px] font-black tracking-widest text-emerald-400 bg-emerald-950/50 border border-emerald-500/30 px-2 py-0.5 rounded-full uppercase">
                                ACTIVE
                            </span>
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-lg font-black text-white uppercase tracking-wider">MLB Predictor Engine</h4>
                            <p className="text-xs text-slate-400 leading-relaxed font-semibold">
                                Complete baseball forecasting. Covers daily moneyline win probabilities, run lines, first-inning NRFI/YRFI, ballpark ballistics weather adjustments, and pitcher matchup edges.
                            </p>
                        </div>
                        <div className="flex justify-between items-center text-[10px] text-blue-400 font-black uppercase tracking-widest pt-2 border-t border-slate-950">
                            <span>Open MLB Dashboard</span>
                            <span className="group-hover:translate-x-1.5 transition-transform duration-300">→</span>
                        </div>
                    </div>

                    <div
                        onClick={() => setActiveSport('tennis')}
                        className="group bg-slate-900/30 border border-slate-850 rounded-3xl p-6 hover:border-indigo-500/30 hover:shadow-[0_10px_30px_rgba(99,102,241,0.1)] transition-all duration-300 cursor-pointer flex flex-col justify-between gap-6 relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 rounded-full blur-xl group-hover:bg-indigo-500/10 transition-colors pointer-events-none"></div>
                        <div className="flex justify-between items-start">
                            <span className="text-3xl leading-none">🎾</span>
                            <span className="text-[8px] font-black tracking-widest text-emerald-400 bg-emerald-950/50 border border-emerald-500/30 px-2 py-0.5 rounded-full uppercase">
                                ACTIVE
                            </span>
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-lg font-black text-white uppercase tracking-wider">Tennis Predictor</h4>
                            <p className="text-xs text-slate-400 leading-relaxed font-semibold">
                                Markov chain-based set/match forecasting. Simulates player match-ups point-by-point to generate margins, total game thresholds, and edge calculations on major tournaments.
                            </p>
                        </div>
                        <div className="flex justify-between items-center text-[10px] text-indigo-400 font-black uppercase tracking-widest pt-2 border-t border-slate-950">
                            <span>Open Tennis Dashboard</span>
                            <span className="group-hover:translate-x-1.5 transition-transform duration-300">→</span>
                        </div>
                    </div>

                    <div
                        onClick={() => setActiveSport('wnba')}
                        className="group bg-slate-900/30 border border-orange-500/20 rounded-3xl p-6 hover:border-orange-400/40 hover:shadow-[0_10px_30px_rgba(249,115,22,0.12)] transition-all duration-300 cursor-pointer flex flex-col justify-between gap-6 relative overflow-hidden"
                    >
                        <div className="absolute top-0 right-0 w-24 h-24 bg-orange-500/5 rounded-full blur-xl group-hover:bg-orange-500/10 transition-colors pointer-events-none" />
                        <div className="flex justify-between items-start">
                            <span className="text-3xl leading-none">🏀</span>
                            <div className="flex flex-col items-end gap-1">
                                <span className="text-[8px] font-black tracking-widest text-cyan-400 bg-cyan-950/50 border border-cyan-500/30 px-2 py-0.5 rounded-full uppercase">
                                    BETA LIVE
                                </span>
                                {wnbaMeta.win_accuracy != null && (
                                    <span className="text-[8px] font-black text-emerald-400 bg-emerald-950/40 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                                        {(wnbaMeta.win_accuracy * 100).toFixed(1)}% Win Acc.
                                    </span>
                                )}
                            </div>
                        </div>
                        <div className="space-y-2">
                            <h4 className="text-lg font-black text-white uppercase tracking-wider">WNBA Predictor Engine</h4>
                            <p className="text-xs text-slate-400 leading-relaxed font-semibold">
                                XGBoost + ELO models for WNBA pace, rest fatigue, star absence, and team ratings. Moneyline, spread, and total projections.
                            </p>
                            <div className="grid grid-cols-3 gap-2 pt-1">
                                <div className="bg-slate-950/50 border border-slate-900 rounded-xl p-2 text-center">
                                    <span className="text-[7px] text-slate-500 font-black uppercase block">Today</span>
                                    <span className="text-sm font-black text-white">{wnbaGames.length}</span>
                                </div>
                                <div className="bg-slate-950/50 border border-slate-900 rounded-xl p-2 text-center">
                                    <span className="text-[7px] text-slate-500 font-black uppercase block">Plays</span>
                                    <span className="text-sm font-black text-indigo-400">
                                        {wnbaGames.reduce((s, g) => s + (g.bet_count || 0), 0)}
                                    </span>
                                </div>
                                <div className="bg-slate-950/50 border border-slate-900 rounded-xl p-2 text-center">
                                    <span className="text-[7px] text-slate-500 font-black uppercase block">Top Edge</span>
                                    <span className="text-sm font-black text-emerald-400 truncate block">
                                        {wnbaTopPlay ? `+${wnbaTopPlay.bet.edge.toFixed(1)}%` : '—'}
                                    </span>
                                </div>
                            </div>
                            {wnbaTopPlay && (
                                <p className="text-[9px] text-slate-500 font-bold">
                                    Best play: <span className="text-orange-400 font-black">{wnbaTopPlay.bet.pick}</span>
                                </p>
                            )}
                        </div>
                        <div className="flex justify-between items-center text-[10px] text-orange-400 font-black uppercase tracking-widest pt-2 border-t border-slate-950">
                            <span>Open WNBA Dashboard</span>
                            <span className="group-hover:translate-x-1.5 transition-transform duration-300">→</span>
                        </div>
                    </div>

                    <div className="bg-slate-900/10 border border-slate-900/60 rounded-3xl p-6 flex flex-col justify-between gap-6 relative overflow-hidden opacity-60 hover:opacity-100 hover:border-slate-850 transition-all duration-300">
                        <div className="flex justify-between items-start">
                            <span className="text-3xl leading-none">🏀</span>
                            <span className="text-[8px] font-black tracking-widest text-slate-500 bg-slate-950/60 border border-slate-900 px-2 py-0.5 rounded-full uppercase">
                                COMING SOON
                            </span>
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-lg font-black text-slate-400 uppercase tracking-wider">NBA Predictor</h4>
                            <p className="text-xs text-slate-500 leading-relaxed font-medium">
                                Positional match-up rating matrices and offensive/defensive ratings. Projecting point margins, quarter-by-quarter points, and prop lines for upcoming basketball matchups.
                            </p>
                        </div>
                        <div className="text-[10px] text-slate-600 font-bold uppercase tracking-widest pt-2 border-t border-slate-950">
                            Warming Up for Next Season
                        </div>
                    </div>

                    <div className="bg-slate-900/10 border border-slate-900/60 rounded-3xl p-6 flex flex-col justify-between gap-6 relative overflow-hidden opacity-60">
                        <div className="flex justify-between items-start">
                            <span className="text-3xl leading-none">⚽</span>
                            <span className="text-[8px] font-black tracking-widest text-slate-500 bg-slate-950/60 border border-slate-900 px-2 py-0.5 rounded-full uppercase">
                                COMING SOON
                            </span>
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-lg font-black text-slate-400 uppercase tracking-wider">Soccer Predictor</h4>
                            <p className="text-xs text-slate-500 leading-relaxed font-medium">
                                xG (Expected Goals) based match simulator. Foreseeing match-outcomes (1X2), total goals (over/under), and both-teams-to-score probabilities across top European leagues.
                            </p>
                        </div>
                        <div className="text-[10px] text-slate-600 font-bold uppercase tracking-widest pt-2 border-t border-slate-950">
                            Model Integration Pending
                        </div>
                    </div>

                    <div className="bg-slate-900/10 border border-slate-900/60 rounded-3xl p-6 flex flex-col justify-between gap-6 relative overflow-hidden opacity-60">
                        <div className="flex justify-between items-start">
                            <span className="text-3xl leading-none">🥊</span>
                            <span className="text-[8px] font-black tracking-widest text-slate-500 bg-slate-950/60 border border-slate-900 px-2 py-0.5 rounded-full uppercase">
                                COMING SOON
                            </span>
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-lg font-black text-slate-400 uppercase tracking-wider">UFC Predictor</h4>
                            <p className="text-xs text-slate-500 leading-relaxed font-medium">
                                Fighter statistics ELO, striking rate matrices, takedown efficiency metrics, and stamina curves simulator. Projecting fight winners, method of victory, and round durations.
                            </p>
                        </div>
                        <div className="text-[10px] text-slate-600 font-bold uppercase tracking-widest pt-2 border-t border-slate-950">
                            Model Development Pending
                        </div>
                    </div>

                    <div className="bg-slate-900/10 border border-slate-900/60 rounded-3xl p-6 flex flex-col justify-between gap-6 relative overflow-hidden opacity-60">
                        <div className="flex justify-between items-start">
                            <span className="text-3xl leading-none">🏈</span>
                            <span className="text-[8px] font-black tracking-widest text-slate-500 bg-slate-950/60 border border-slate-900 px-2 py-0.5 rounded-full uppercase">
                                COMING SOON
                            </span>
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-lg font-black text-slate-400 uppercase tracking-wider">NFL Predictor</h4>
                            <p className="text-xs text-slate-500 leading-relaxed font-medium">
                                Drive efficiency models, DVOA-based team ratings, and QB performance metrics. Forecasting spreads, totals, and player prop lines across all 32 teams.
                            </p>
                        </div>
                        <div className="text-[10px] text-slate-600 font-bold uppercase tracking-widest pt-2 border-t border-slate-950">
                            Model Development Pending
                        </div>
                    </div>

                    <div className="bg-slate-900/10 border border-slate-900/60 rounded-3xl p-6 flex flex-col justify-between gap-6 relative overflow-hidden opacity-60">
                        <div className="flex justify-between items-start">
                            <span className="text-3xl leading-none">🏒</span>
                            <span className="text-[8px] font-black tracking-widest text-slate-500 bg-slate-950/60 border border-slate-900 px-2 py-0.5 rounded-full uppercase">
                                COMING SOON
                            </span>
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-lg font-black text-slate-400 uppercase tracking-wider">NHL Predictor</h4>
                            <p className="text-xs text-slate-500 leading-relaxed font-medium">
                                Corsi/Fenwick possession metrics, goalie save-percentage models, and power-play efficiency ratings. Projecting puck-line, totals, and period-by-period outcomes.
                            </p>
                        </div>
                        <div className="text-[10px] text-slate-600 font-bold uppercase tracking-widest pt-2 border-t border-slate-950">
                            Model Development Pending
                        </div>
                    </div>

                    <div className="bg-slate-900/10 border border-slate-900/60 rounded-3xl p-6 flex flex-col justify-between gap-6 relative overflow-hidden opacity-60">
                        <div className="flex justify-between items-start">
                            <span className="text-3xl leading-none">🏀</span>
                            <span className="text-[8px] font-black tracking-widest text-slate-500 bg-slate-950/60 border border-slate-900 px-2 py-0.5 rounded-full uppercase">
                                COMING SOON
                            </span>
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-lg font-black text-slate-400 uppercase tracking-wider">CBB Predictor</h4>
                            <p className="text-xs text-slate-500 leading-relaxed font-medium">
                                KenPom efficiency ratings, adjusted tempo, and tournament seed models. Forecasting spreads, totals, and March Madness bracket probabilities.
                            </p>
                        </div>
                        <div className="text-[10px] text-slate-600 font-bold uppercase tracking-widest pt-2 border-t border-slate-950">
                            Model Development Pending
                        </div>
                    </div>

                    <div className="bg-slate-900/10 border border-slate-900/60 rounded-3xl p-6 flex flex-col justify-between gap-6 relative overflow-hidden opacity-60">
                        <div className="flex justify-between items-start">
                            <span className="text-3xl leading-none">🏈</span>
                            <span className="text-[8px] font-black tracking-widest text-slate-500 bg-slate-950/60 border border-slate-900 px-2 py-0.5 rounded-full uppercase">
                                COMING SOON
                            </span>
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-lg font-black text-slate-400 uppercase tracking-wider">CFB Predictor</h4>
                            <p className="text-xs text-slate-500 leading-relaxed font-medium">
                                SP+ and FPI rating-based game-flow simulator. Projecting spread, total, and moneyline outcomes across Power conferences and bowl matchups.
                            </p>
                        </div>
                        <div className="text-[10px] text-slate-600 font-bold uppercase tracking-widest pt-2 border-t border-slate-950">
                            Model Development Pending
                        </div>
                    </div>

                    <div className="bg-slate-900/10 border border-slate-900/60 rounded-3xl p-6 flex flex-col justify-between gap-6 relative overflow-hidden opacity-60">
                        <div className="flex justify-between items-start">
                            <span className="text-3xl leading-none">⛳</span>
                            <span className="text-[8px] font-black tracking-widest text-slate-500 bg-slate-950/60 border border-slate-900 px-2 py-0.5 rounded-full uppercase">
                                COMING SOON
                            </span>
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-lg font-black text-slate-400 uppercase tracking-wider">PGA Tour Predictor</h4>
                            <p className="text-xs text-slate-500 leading-relaxed font-medium">
                                Strokes Gained (SG) multi-factor models. Projecting Top 5/10/15 finish probabilities, matchup winners, and 3-ball outcomes across all PGA Tour events.
                            </p>
                        </div>
                        <div className="text-[10px] text-slate-600 font-bold uppercase tracking-widest pt-2 border-t border-slate-950">
                            Model Development Pending
                        </div>
                    </div>
                </div>
            </div>

            {/* ================= BLOK 6: LEAGUE STANDINGS & WORLD RANKINGS ================= */}
            <div className="space-y-4">
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                    
                    {/* MLB Standings Column */}
                    <div className="space-y-4">
                        <span className="text-[10px] md:text-xs font-black text-slate-500 uppercase tracking-[0.2em] px-1 block text-center sm:text-left">
                            ⚾ MLB Division Standings (Key Matchup Context)
                        </span>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {/* AL East */}
                            <div className="bg-slate-900/30 border border-slate-850 rounded-3xl p-5 shadow-lg relative overflow-hidden">
                                <div className="flex justify-between items-center mb-3.5 border-b border-slate-950 pb-2">
                                    <span className="text-xs font-black text-white uppercase tracking-wider">AL East Division</span>
                                    <span className="text-[9px] text-slate-500 font-bold">2026 Season</span>
                                </div>
                                {standingsLoading ? (
                                    <div className="space-y-3 py-2 animate-pulse">
                                        {[1, 2, 3, 4, 5].map(i => (
                                            <div key={i} className="h-4 bg-slate-800/20 rounded w-full"></div>
                                        ))}
                                    </div>
                                ) : !alEast ? (
                                    <div className="py-8 text-center text-slate-500 text-xs font-bold uppercase tracking-wider">
                                        Standings currently unavailable
                                    </div>
                                ) : (
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-left border-collapse">
                                            <thead>
                                                <tr className="border-b border-slate-950 text-[9px] text-slate-500 font-black uppercase tracking-wider">
                                                    <th className="pb-2">Team</th>
                                                    <th className="pb-2 text-center">W</th>
                                                    <th className="pb-2 text-center">L</th>
                                                    <th className="pb-2 text-center">GB</th>
                                                    <th className="pb-2 text-right">L10</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-950/40 text-xs text-gray-300">
                                                {alEast.map((team, idx) => (
                                                    <tr key={team.name} className="hover:bg-slate-900/30 transition-colors">
                                                        <td className="py-2.5 font-bold flex items-center gap-1.5">
                                                            {idx === 0 && <span className="text-[10px]">👑</span>}
                                                            {team.name}
                                                        </td>
                                                        <td className="py-2.5 text-center font-extrabold">{team.wins}</td>
                                                        <td className="py-2.5 text-center font-extrabold text-slate-400">{team.losses}</td>
                                                        <td className="py-2.5 text-center text-slate-400 font-bold">{team.gb}</td>
                                                        <td className={`py-2.5 text-right font-semibold ${parseInt(team.l10.split('-')[0]) >= 5 ? 'text-emerald-400' : 'text-rose-500'}`}>{team.l10}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>

                            {/* NL West */}
                            <div className="bg-slate-900/30 border border-slate-850 rounded-3xl p-5 shadow-lg relative overflow-hidden">
                                <div className="flex justify-between items-center mb-3.5 border-b border-slate-950 pb-2">
                                    <span className="text-xs font-black text-white uppercase tracking-wider">NL West Division</span>
                                    <span className="text-[9px] text-slate-500 font-bold">2026 Season</span>
                                </div>
                                {standingsLoading ? (
                                    <div className="space-y-3 py-2 animate-pulse">
                                        {[1, 2, 3, 4, 5].map(i => (
                                            <div key={i} className="h-4 bg-slate-800/20 rounded w-full"></div>
                                        ))}
                                    </div>
                                ) : !nlWest ? (
                                    <div className="py-8 text-center text-slate-500 text-xs font-bold uppercase tracking-wider">
                                        Standings currently unavailable
                                    </div>
                                ) : (
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-left border-collapse">
                                            <thead>
                                                <tr className="border-b border-slate-950 text-[9px] text-slate-500 font-black uppercase tracking-wider">
                                                    <th className="pb-2">Team</th>
                                                    <th className="pb-2 text-center">W</th>
                                                    <th className="pb-2 text-center">L</th>
                                                    <th className="pb-2 text-center">GB</th>
                                                    <th className="pb-2 text-right">L10</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-950/40 text-xs text-gray-300">
                                                {nlWest.map((team, idx) => (
                                                    <tr key={team.name} className="hover:bg-slate-900/30 transition-colors">
                                                        <td className="py-2.5 font-bold flex items-center gap-1.5">
                                                            {idx === 0 && <span className="text-[10px]">👑</span>}
                                                            {team.name}
                                                        </td>
                                                        <td className="py-2.5 text-center font-extrabold">{team.wins}</td>
                                                        <td className="py-2.5 text-center font-extrabold text-slate-400">{team.losses}</td>
                                                        <td className="py-2.5 text-center text-slate-400 font-bold">{team.gb}</td>
                                                        <td className={`py-2.5 text-right font-semibold ${parseInt(team.l10.split('-')[0]) >= 5 ? 'text-emerald-400' : 'text-rose-500'}`}>{team.l10}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Tennis Rankings Column */}
                    <div className="space-y-4">
                        <span className="text-[10px] md:text-xs font-black text-slate-500 uppercase tracking-[0.2em] px-1 block text-center sm:text-left">
                            🎾 ATP & WTA World Rankings (Player Context)
                        </span>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {/* ATP Top 5 */}
                            <div className="bg-slate-900/30 border border-slate-850 rounded-3xl p-5 shadow-lg relative overflow-hidden">
                                <div className="flex justify-between items-center mb-3.5 border-b border-slate-950 pb-2">
                                    <span className="text-xs font-black text-white uppercase tracking-wider">ATP Top 5 Players</span>
                                    <span className="text-[9px] text-slate-500 font-bold">Singles Ranks</span>
                                </div>
                                {rankingsLoading ? (
                                    <div className="space-y-3 py-2 animate-pulse">
                                        {[1, 2, 3, 4, 5].map(i => (
                                            <div key={i} className="h-4 bg-slate-800/20 rounded w-full"></div>
                                        ))}
                                    </div>
                                ) : (!rankingsData || !rankingsData.atp || rankingsData.atp.length === 0) ? (
                                    <div className="py-8 text-center text-slate-500 text-xs font-bold uppercase tracking-wider">
                                        Rankings currently unavailable
                                    </div>
                                ) : (
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-left border-collapse">
                                            <thead>
                                                <tr className="border-b border-slate-950 text-[9px] text-slate-500 font-black uppercase tracking-wider">
                                                    <th className="pb-2">Rank</th>
                                                    <th className="pb-2">Player</th>
                                                    <th className="pb-2 text-right">Points</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-950/40 text-xs text-gray-300">
                                                {rankingsData.atp.map((player) => (
                                                    <tr key={player.id} className="hover:bg-slate-900/30 transition-colors">
                                                        <td className="py-2.5 font-extrabold text-indigo-400">#{player.rank}</td>
                                                        <td className="py-2.5 font-bold">
                                                            <div className="truncate max-w-[120px]">{player.name}</div>
                                                            <div className="text-[9px] text-slate-500 font-medium">{player.country}</div>
                                                        </td>
                                                        <td className="py-2.5 text-right font-extrabold text-slate-400">{player.points.toLocaleString()}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>

                            {/* WTA Top 5 */}
                            <div className="bg-slate-900/30 border border-slate-850 rounded-3xl p-5 shadow-lg relative overflow-hidden">
                                <div className="flex justify-between items-center mb-3.5 border-b border-slate-950 pb-2">
                                    <span className="text-xs font-black text-white uppercase tracking-wider">WTA Top 5 Players</span>
                                    <span className="text-[9px] text-slate-500 font-bold">Singles Ranks</span>
                                </div>
                                {rankingsLoading ? (
                                    <div className="space-y-3 py-2 animate-pulse">
                                        {[1, 2, 3, 4, 5].map(i => (
                                            <div key={i} className="h-4 bg-slate-800/20 rounded w-full"></div>
                                        ))}
                                    </div>
                                ) : (!rankingsData || !rankingsData.wta || rankingsData.wta.length === 0) ? (
                                    <div className="py-8 text-center text-slate-500 text-xs font-bold uppercase tracking-wider">
                                        Rankings currently unavailable
                                    </div>
                                ) : (
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-left border-collapse">
                                            <thead>
                                                <tr className="border-b border-slate-950 text-[9px] text-slate-500 font-black uppercase tracking-wider">
                                                    <th className="pb-2">Rank</th>
                                                    <th className="pb-2">Player</th>
                                                    <th className="pb-2 text-right">Points</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-950/40 text-xs text-gray-300">
                                                {rankingsData.wta.map((player) => (
                                                    <tr key={player.id} className="hover:bg-slate-900/30 transition-colors">
                                                        <td className="py-2.5 font-extrabold text-indigo-400">#{player.rank}</td>
                                                        <td className="py-2.5 font-bold">
                                                            <div className="truncate max-w-[120px]">{player.name}</div>
                                                            <div className="text-[9px] text-slate-500 font-medium">{player.country}</div>
                                                        </td>
                                                        <td className="py-2.5 text-right font-extrabold text-slate-400">{player.points.toLocaleString()}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* ================= BLOK 5: MODEL ARCHITECTURE ================= */}
            <div className="space-y-4">
                <span className="text-[10px] md:text-xs font-black text-slate-500 uppercase tracking-[0.2em] px-1 block text-center sm:text-left">
                    🧠 Platform Core Intelligence
                </span>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-slate-900/40 border border-slate-850 rounded-2xl p-5 space-y-3">
                        <div className="text-xl">🏟️</div>
                        <h5 className="text-xs font-black text-white uppercase tracking-wider">Ballpark Ballistics</h5>
                        <p className="text-[10.5px] text-slate-400 leading-relaxed font-medium">
                            Adjusts batting flyball carries in real-time. The model incorporates elevation, humidity, temperature, and wind vector grids to shift projected runs by up to 18% per stadium.
                        </p>
                    </div>

                    <div className="bg-slate-900/40 border border-slate-850 rounded-2xl p-5 space-y-3">
                        <div className="text-xl">📊</div>
                        <h5 className="text-xs font-black text-white uppercase tracking-wider">CDF Probability Curves</h5>
                        <p className="text-[10.5px] text-slate-400 leading-relaxed font-medium">
                            Transforms projected runs into cover probabilities. Using a custom Normal Cumulative Distribution Function (CDF) tuned to modern baseball margins, we check bookmaker spreads.
                        </p>
                    </div>

                    <div className="bg-slate-900/40 border border-slate-850 rounded-2xl p-5 space-y-3">
                        <div className="text-xl">⛓️</div>
                        <h5 className="text-xs font-black text-white uppercase tracking-wider">Markov Point Chains</h5>
                        <p className="text-[10.5px] text-slate-400 leading-relaxed font-medium">
                            Calculates tennis outcomes point-by-point. Modulating players' serving and receiving effectiveness, the model executes a recursive chain to output exact set and game outcomes.
                        </p>
                    </div>
                </div>
            </div>

        </div>
    );
}

export default CentralDashboard;
