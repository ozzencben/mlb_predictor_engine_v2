import React, { useState, useMemo, useEffect } from 'react';
import { usePredictions } from './hooks/usePredictions';
import MatchupCard from './components/MatchupCard';
import MatchupSkeleton from './components/MatchupSkeleton';
import Footer from './components/Footer';
import NrfiRow from './components/NrfiRow';
import logo2Img from './assets/logo2.png';
import { getTeamAbbr } from './utils/formatters';

// Cumulative normal distribution CDF using math approximation for erf (to support Spread Probability)
const normalCDF = (x, mean = 0, stdDev = 1) => {
    const z = (x - mean) / stdDev;
    const t = 1.0 / (1.0 + 0.5 * Math.abs(z));
    const ans = 1.0 - t * Math.exp(-z * z - 1.26551223 +
        t * (1.00002368 +
        t * (0.37409196 +
        t * (0.09678418 +
        t * (-0.18628806 +
        t * (0.27886807 +
        t * (-1.13520398 +
        t * (1.48851587 +
        t * (-0.82215223 +
        t * 0.17087277)))))))));
    return z >= 0 ? 0.5 + 0.5 * ans : 0.5 - 0.5 * ans;
};

function App() {
  const [selectedDate, setSelectedDate] = useState(null);
  const [activeModel, setActiveModel] = useState('full'); // 'full', 'nrfi', 'f5'
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [isSlowLoading, setIsSlowLoading] = useState(false);
  const { data, loading, error, isPreparing } = usePredictions(selectedDate);

  useEffect(() => {
    if (loading) {
      const timer = setTimeout(() => {
        setIsSlowLoading(true);
      }, 3000);
      return () => clearTimeout(timer);
    } else {
      setIsSlowLoading(false);
    }
  }, [loading]);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 300) {
        setShowScrollTop(true);
      } else {
        setShowScrollTop(false);
      }
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const getOffsetDateString = (offset) => {
    const d = new Date();
    const etString = d.toLocaleString("en-US", { timeZone: "America/New_York" });
    const etDate = new Date(etString);
    etDate.setDate(etDate.getDate() + offset);
    
    const yyyy = etDate.getFullYear();
    const mm = String(etDate.getMonth() + 1).padStart(2, '0');
    const dd = String(etDate.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };

  const formatDateLabel = (dateStr) => {
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    if (parts.length !== 3) return dateStr;
    const year = parseInt(parts[0]);
    const month = parseInt(parts[1]) - 1;
    const day = parseInt(parts[2]);
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return `${months[month]} ${day}`;
  };

  const calendarDays = useMemo(() => {
    const days = [];
    for (let i = -2; i <= 2; i++) {
      days.push({
        dateStr: getOffsetDateString(i),
        offset: i,
      });
    }
    return days;
  }, []);

  const onNavigateToNrfi = (gameKey) => {
    setActiveModel('nrfi');
    setTimeout(() => {
      const element = document.getElementById(`nrfi-card-${gameKey}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Add dynamic glowing indicator for visual delight
        element.classList.add('ring-4', 'ring-indigo-500/80', 'shadow-[0_0_30px_rgba(99,102,241,0.6)]', 'transition-all', 'duration-500', 'scale-[1.015]');
        setTimeout(() => {
          element.classList.remove('ring-4', 'ring-indigo-500/80', 'shadow-[0_0_30px_rgba(99,102,241,0.6)]', 'scale-[1.015]');
        }, 3000);
      }
    }, 150);
  };

  // 503: Veri hazırlanıyor (zamanlayıcı henüz çalışmamış) veya polling durumunda
  if (isPreparing) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-slate-950 text-gray-100 selection:bg-indigo-500 selection:text-white">
        <div className="bg-slate-900/60 backdrop-blur-xl border border-indigo-500/30 rounded-3xl p-8 md:p-10 text-center max-w-lg shadow-[0_0_50px_rgba(99,102,241,0.15)] flex flex-col items-center">
          <div className="relative mb-6">
            <span className="text-6xl inline-block animate-spin [animation-duration:3s]">⚾</span>
            <div className="absolute inset-0 rounded-full bg-indigo-500/10 blur-xl animate-pulse"></div>
          </div>
          <h2 className="text-xl md:text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-indigo-400 to-purple-400 uppercase tracking-widest mb-3">
            Legends AI Warming Up
          </h2>
          <p className="text-gray-300 text-sm md:text-base font-semibold leading-relaxed mb-6">
            Calculations are in progress! The model is active and updating lineups, live betting lines, and ballpark wind metrics for today's matches.
          </p>
          <div className="w-full bg-slate-950/80 rounded-full h-1.5 p-[1px] border border-slate-800 mb-6 relative overflow-hidden">
            <div className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 rounded-full w-2/3 animate-pulse shadow-[0_0_10px_rgba(99,102,241,0.5)]"></div>
          </div>
          <div className="flex items-center gap-2 px-4 py-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-full">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
            </span>
            <span className="text-[10px] md:text-xs text-indigo-300 font-extrabold uppercase tracking-widest animate-pulse">
              Polling Server... Dashboard Autoload Active
            </span>
          </div>
          <p className="text-[9px] text-gray-400 mt-8 font-black uppercase tracking-[0.2em]">
            Legends Sports MLB Predictor Engine
          </p>
        </div>
      </div>
    );
  }

  if (error) return <div className="p-10 text-red-500 text-center font-black">❌ Connection Error: {error}</div>;

  const predictions = data?.data?.predictions || [];
  const systemDate = data?.data?.date || '';
  const lastUpdated = data?.last_updated;

  const scrollToMatchup = (awayTeam, homeTeam) => {
    setActiveModel('full');
    setTimeout(() => {
      const element = document.getElementById(`matchup-card-${awayTeam}-${homeTeam}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Add dynamic glowing ring indicator
        element.classList.add('ring-4', 'ring-blue-500/80', 'shadow-[0_0_30px_rgba(59,130,246,0.6)]', 'transition-all', 'duration-500', 'scale-[1.01]');
        setTimeout(() => {
          element.classList.remove('ring-4', 'ring-blue-500/80', 'shadow-[0_0_30px_rgba(59,130,246,0.6)]', 'scale-[1.01]');
        }, 3000);
      }
    }, 150);
  };

  const dailyEdges = useMemo(() => {
    if (!predictions || predictions.length === 0) return null;

    let topMlGame = null;
    let topMlEdgeVal = -999;
    let topMlChoice = '';
    let topMlProb = 0;

    let topSpreadGame = null;
    let topSpreadProbVal = 0;
    let topSpreadChoice = '';

    let topTotalGame = null;
    let topTotalGapVal = -1;
    let topTotalChoice = '';
    let topTotalModelVal = 0;

    predictions.forEach((game) => {
      const { matchup, Full_Game, Odds } = game;
      if (!matchup || !Full_Game) return;

      // --- 1. Moneyline Edge ---
      const awayProb = parseFloat(Full_Game.full_away_win_prob || 0);
      const homeProb = parseFloat(Full_Game.full_home_win_prob || 0);
      const awayEdge = parseFloat(Odds?.away_edge_pct || 0);
      const homeEdge = parseFloat(Odds?.home_edge_pct || 0);

      const isAwayMlBetter = awayEdge >= homeEdge;
      const maxMlEdge = isAwayMlBetter ? awayEdge : homeEdge;
      const mlChoice = isAwayMlBetter ? `${getTeamAbbr(matchup.away_team)} ML` : `${getTeamAbbr(matchup.home_team)} ML`;
      const mlProb = isAwayMlBetter ? awayProb : homeProb;

      if (maxMlEdge > topMlEdgeVal) {
        topMlEdgeVal = maxMlEdge;
        topMlGame = game;
        topMlChoice = mlChoice;
        topMlProb = mlProb;
      }

      // --- 2. Spread Edge (Probability) ---
      const awayScore = parseFloat(Full_Game.full_away_score || 0);
      const homeScore = parseFloat(Full_Game.full_home_score || 0);
      const mu = homeScore - awayScore;
      const sigma = 4.0;

      const homeCoverMinus1_5 = 1 - normalCDF(1.5, mu, sigma);
      const homeCoverPlus1_5 = 1 - normalCDF(-1.5, mu, sigma);
      const awayCoverMinus1_5 = normalCDF(-1.5, mu, sigma);
      const awayCoverPlus1_5 = normalCDF(1.5, mu, sigma);

      const bookAwaySpread = Odds?.away_spread !== undefined ? Odds.away_spread : (awayScore > homeScore ? -1.5 : 1.5);
      const isAwaySpreadFav = bookAwaySpread < 0;
      const spreadLineFav = isAwaySpreadFav ? matchup.away_team : matchup.home_team;
      const spreadLineDog = isAwaySpreadFav ? matchup.home_team : matchup.away_team;

      const pMinus1_5_Fav = isAwaySpreadFav ? awayCoverMinus1_5 : homeCoverMinus1_5;
      const pPlus1_5_Dog = isAwaySpreadFav ? homeCoverPlus1_5 : awayCoverPlus1_5;

      let spreadChoice = "";
      let spreadProb = 0;
      if (pMinus1_5_Fav >= 0.5) {
        spreadChoice = `${getTeamAbbr(spreadLineFav)} -1.5`;
        spreadProb = pMinus1_5_Fav;
      } else {
        spreadChoice = `${getTeamAbbr(spreadLineDog)} +1.5`;
        spreadProb = pPlus1_5_Dog;
      }

      if (spreadProb > topSpreadProbVal) {
        topSpreadProbVal = spreadProb;
        topSpreadGame = game;
        topSpreadChoice = spreadChoice;
      }

      // --- 3. Total Edge ---
      const bookTotal = Odds?.over_under !== undefined && Odds.over_under > 0 ? Odds.over_under : 8.5;
      const modelTotal = parseFloat(Full_Game.full_total || 0);
      const totalGap = Math.abs(modelTotal - bookTotal);
      const totalChoice = modelTotal >= bookTotal ? `OVER ${bookTotal}` : `UNDER ${bookTotal}`;

      if (totalGap > topTotalGapVal) {
        topTotalGapVal = totalGap;
        topTotalGame = game;
        topTotalChoice = totalChoice;
        topTotalModelVal = modelTotal;
      }
    });

    return {
      ml: topMlGame ? { game: topMlGame, edge: topMlEdgeVal, choice: topMlChoice, prob: topMlProb } : null,
      spread: topSpreadGame ? { game: topSpreadGame, prob: topSpreadProbVal, choice: topSpreadChoice } : null,
      total: topTotalGame ? { game: topTotalGame, gap: topTotalGapVal, choice: topTotalChoice, modelTotal: topTotalModelVal } : null
    };
  }, [predictions]);

  // Sort NRFI predictions from highest AI score to least when active, filtering out games without NRFI data
  const displayPredictions = activeModel === 'nrfi'
    ? predictions.filter(game => game.NRFI && game.NRFI.pick)
                 .sort((a, b) => (b.NRFI?.confidence || 0) - (a.NRFI?.confidence || 0))
    : predictions;

  return (
    <div className="min-h-screen bg-slate-950 text-gray-100 relative overflow-hidden w-full selection:bg-indigo-500 selection:text-white pb-10">
      {/* Abstract Background Blur Blobs for Premium Depth */}
      <div className="absolute top-10 left-1/4 w-72 h-72 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none animate-pulse duration-[8s]"></div>
      <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none animate-pulse duration-[12s]"></div>
      <div className="absolute top-1/2 left-1/3 w-80 h-80 bg-purple-500/5 rounded-full blur-3xl pointer-events-none"></div>

      <main className="max-w-4xl mx-auto p-4 md:p-8 relative z-10">
        {/* ================= HEADER ================= */}
        <header className="mb-10 flex flex-col md:flex-row justify-between md:items-center border-b border-gray-800 pb-6 gap-4 md:gap-0">
          {/* Sol Kısım: Logo ve Başlık */}
          <div className="flex flex-col">
            <h1 className="flex items-center justify-start gap-2 md:gap-3 flex-wrap">
              <img
                src={logo2Img}
                alt="Legends Sports"
                className="h-10 md:h-14 lg:h-16 w-auto object-contain drop-shadow-[0_0_15px_rgba(59,130,246,0.35)] filter brightness-110"
              />
              <span className="text-slate-400 mx-1 md:mx-2 font-light hidden sm:inline text-xl md:text-3xl">|</span>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-indigo-500 text-lg md:text-2xl font-black tracking-widest uppercase mt-0.5">
                MLB Predictions
              </span>
            </h1>
            {/* Masaüstünde logonun altına değil, yazının altına hizalamak istiyorsan buraya ml eklenebilir ama şu anki yapı en temizidir */}
            <p className="text-gray-400 text-sm font-bold tracking-tight mt-1 md:mt-2">
              Data-Driven Insights for {loading ? 'Loading...' : systemDate || 'No Date'}
            </p>
          </div>

          {/* Sağ Kısım: Status ve Update */}
          <div className="flex flex-col items-start md:items-end w-full md:w-auto mt-2 md:mt-0">
            {!loading && lastUpdated && (
              <div className="mb-1">
                <span className="text-[9px] text-slate-400 font-black uppercase tracking-[0.2em]">
                  Last Update: <span className="text-gray-300">{lastUpdated}</span>
                </span>
              </div>
            )}

            <div className="flex flex-col items-start md:items-end">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                System Status
              </span>
              <div className="flex items-center gap-2 mt-0.5">
                <div className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                </div>
                <span className="text-xs font-bold text-green-500 uppercase tracking-tighter">
                  {loading ? 'Syncing...' : 'Live & Ready'}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* ================= CALENDAR TAPE ================= */}
        <div className="mb-8 p-1.5 bg-slate-900/40 backdrop-blur-md border border-slate-800/80 rounded-2xl flex items-center justify-between gap-1 overflow-x-auto no-scrollbar scroll-smooth">
          {calendarDays.map((day) => {
            const isToday = day.offset === 0;
            const isSelected = selectedDate === day.dateStr || (selectedDate === null && isToday);
            
            let relativeLabel = '';
            if (day.offset === -2) relativeLabel = '2 DAYS AGO';
            else if (day.offset === -1) relativeLabel = 'YESTERDAY';
            else if (day.offset === 0) relativeLabel = 'TODAY';
            else if (day.offset === 1) relativeLabel = 'TOMORROW';
            else if (day.offset === 2) relativeLabel = '2 DAYS AWAY';

            return (
              <button
                key={day.dateStr}
                onClick={() => setSelectedDate(isToday ? null : day.dateStr)}
                className={`flex-1 min-w-[90px] md:min-w-[120px] py-2 px-3 flex flex-col items-center justify-center rounded-xl transition-all duration-300 relative group cursor-pointer ${
                  isSelected
                    ? 'bg-gradient-to-br from-indigo-600/90 to-blue-600/90 text-white font-extrabold shadow-[0_0_15px_rgba(99,102,241,0.4)] border border-indigo-400/40 scale-[1.02]'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent'
                }`}
              >
                <span className={`text-[9px] md:text-[10px] uppercase font-black tracking-widest ${
                  isSelected ? 'text-cyan-200' : 'text-slate-500 group-hover:text-slate-400'
                }`}>
                  {relativeLabel}
                </span>
                <span className="text-xs md:text-sm font-bold mt-0.5">
                  {formatDateLabel(day.dateStr)}
                </span>
                {isSelected && (
                  <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)] animate-pulse"></span>
                )}
              </button>
            );
          })}
        </div>

        {/* ================= BACKEND COLD START WARNING ================= */}
        {loading && isSlowLoading && (
          <div className="mb-8 p-6 bg-indigo-950/40 backdrop-blur-xl border border-indigo-500/30 rounded-2xl text-center flex flex-col items-center justify-center shadow-[0_0_30px_rgba(99,102,241,0.15)] animate-pulse select-none">
            <span className="text-4xl block mb-3 animate-spin [animation-duration:4s]">⚡</span>
            <h4 className="text-sm md:text-base font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-indigo-400 uppercase tracking-widest mb-1.5">
              Waking Up Predictor Server
            </h4>
            <p className="text-gray-300 text-xs md:text-sm max-w-md font-semibold leading-relaxed mb-4">
              Since the engine is hosted on Render's free tier, the backend container automatically hibernates after inactivity. We are waking it up now—this process typically takes about 45-60 seconds. Thank you for your patience!
            </p>
            <div className="flex items-center gap-2 px-3 py-1 bg-cyan-500/10 border border-cyan-500/20 rounded-full">
              <span className="flex h-1.5 w-1.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-cyan-500"></span>
              </span>
              <span className="text-[9px] text-cyan-300 font-extrabold uppercase tracking-wider">
                Connecting to API container...
              </span>
            </div>
          </div>
        )}

        {!loading && dailyEdges && predictions.length > 0 && (
          <div className="bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-4 sm:p-5 shadow-[0_8px_32px_rgba(0,0,0,0.4)] mb-8 select-none border-t border-t-indigo-500/30">
            <div className="flex justify-between items-center mb-4 border-b border-slate-800 pb-2.5">
              <div className="flex items-center gap-2">
                <span className="text-xl leading-none animate-pulse">⚡</span>
                <span className="text-xs md:text-sm font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-indigo-400 to-purple-400 uppercase tracking-widest">
                  VIP Consensus Edges
                </span>
              </div>
              <span className="text-[9px] text-indigo-400 font-extrabold uppercase tracking-widest bg-indigo-950/80 border border-indigo-500/25 px-2 py-0.5 rounded-full animate-bounce">
                🔥 Top Picks
              </span>
            </div>

            {/* Flex layout that is scrollable on mobile */}
            <div className="flex flex-row overflow-x-auto no-scrollbar gap-4 pb-1 -mx-2 px-2 scroll-smooth snap-x snap-mandatory">
              {/* ML Edge Card */}
              {dailyEdges.ml && (
                <div 
                  onClick={() => scrollToMatchup(dailyEdges.ml.game.matchup.away_team, dailyEdges.ml.game.matchup.home_team)}
                  className="flex-1 min-w-[240px] sm:min-w-0 bg-slate-950/50 border border-emerald-500/20 rounded-xl p-3.5 flex flex-col justify-between cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:border-emerald-500/50 hover:shadow-[0_8px_20px_rgba(16,185,129,0.15)] snap-start relative overflow-hidden group"
                >
                  <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-xl group-hover:bg-emerald-500/10 transition-colors pointer-events-none"></div>
                  <div className="flex justify-between items-start mb-2 gap-2">
                    <span className="text-[9px] text-emerald-400 font-black uppercase tracking-widest bg-emerald-950/60 border border-emerald-500/20 px-1.5 py-0.5 rounded flex-shrink-0">
                      ML Value Edge
                    </span>
                    <span className="text-[9px] text-gray-500 font-bold whitespace-nowrap truncate">
                      {getTeamAbbr(dailyEdges.ml.game.matchup.away_team)} @ {getTeamAbbr(dailyEdges.ml.game.matchup.home_team)}
                    </span>
                  </div>
                  <div className="mt-1">
                    <div className="text-sm font-extrabold text-gray-200">
                      {dailyEdges.ml.choice}
                    </div>
                    <div className="text-xl font-black text-emerald-400 mt-0.5 tracking-tight flex items-baseline gap-1">
                      <span>+{dailyEdges.ml.edge.toFixed(1)}%</span>
                      <span className="text-[10px] text-gray-400 font-bold">Edge</span>
                    </div>
                  </div>
                  <div className="mt-3 flex justify-between items-center text-[9px] text-gray-400 border-t border-slate-900/60 pt-2">
                    <span className="font-semibold text-slate-400">Proj Win: {Math.round(dailyEdges.ml.prob * 100)}%</span>
                    <span className="text-slate-500 group-hover:text-emerald-400 font-black transition-colors uppercase tracking-widest">Analyze →</span>
                  </div>
                </div>
              )}

              {/* Spread Cover Card */}
              {dailyEdges.spread && (
                <div 
                  onClick={() => scrollToMatchup(dailyEdges.spread.game.matchup.away_team, dailyEdges.spread.game.matchup.home_team)}
                  className="flex-1 min-w-[240px] sm:min-w-0 bg-slate-950/50 border border-indigo-500/20 rounded-xl p-3.5 flex flex-col justify-between cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:border-indigo-500/50 hover:shadow-[0_8px_20px_rgba(99,102,241,0.15)] snap-start relative overflow-hidden group"
                >
                  <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 rounded-full blur-xl group-hover:bg-indigo-500/10 transition-colors pointer-events-none"></div>
                  <div className="flex justify-between items-start mb-2 gap-2">
                    <span className="text-[9px] text-indigo-400 font-black uppercase tracking-widest bg-indigo-950/60 border border-indigo-500/20 px-1.5 py-0.5 rounded flex-shrink-0">
                      Spread Cover
                    </span>
                    <span className="text-[9px] text-gray-500 font-bold whitespace-nowrap truncate">
                      {getTeamAbbr(dailyEdges.spread.game.matchup.away_team)} @ {getTeamAbbr(dailyEdges.spread.game.matchup.home_team)}
                    </span>
                  </div>
                  <div className="mt-1">
                    <div className="text-sm font-extrabold text-gray-200">
                      {dailyEdges.spread.choice}
                    </div>
                    <div className="text-xl font-black text-indigo-400 mt-0.5 tracking-tight flex items-baseline gap-1">
                      <span>{Math.round(dailyEdges.spread.prob * 100)}%</span>
                      <span className="text-[10px] text-gray-400 font-bold">Cover Prob</span>
                    </div>
                  </div>
                  <div className="mt-3 flex justify-between items-center text-[9px] text-gray-400 border-t border-slate-900/60 pt-2">
                    <span className="font-semibold text-slate-400">Normal CDF Model</span>
                    <span className="text-slate-500 group-hover:text-indigo-400 font-black transition-colors uppercase tracking-widest">Analyze →</span>
                  </div>
                </div>
              )}

              {/* O/U Variance Card */}
              {dailyEdges.total && (
                <div 
                  onClick={() => scrollToMatchup(dailyEdges.total.game.matchup.away_team, dailyEdges.total.game.matchup.home_team)}
                  className="flex-1 min-w-[240px] sm:min-w-0 bg-slate-950/50 border border-blue-500/20 rounded-xl p-3.5 flex flex-col justify-between cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:border-blue-500/50 hover:shadow-[0_8px_20px_rgba(59,130,246,0.15)] snap-start relative overflow-hidden group"
                >
                  <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-full blur-xl group-hover:bg-blue-500/10 transition-colors pointer-events-none"></div>
                  <div className="flex justify-between items-start mb-2 gap-2">
                    <span className="text-[9px] text-blue-400 font-black uppercase tracking-widest bg-blue-950/60 border border-blue-500/20 px-1.5 py-0.5 rounded flex-shrink-0">
                      Total Variance
                    </span>
                    <span className="text-[9px] text-gray-500 font-bold whitespace-nowrap truncate">
                      {getTeamAbbr(dailyEdges.total.game.matchup.away_team)} @ {getTeamAbbr(dailyEdges.total.game.matchup.home_team)}
                    </span>
                  </div>
                  <div className="mt-1">
                    <div className="text-sm font-extrabold text-gray-200">
                      {dailyEdges.total.choice}
                    </div>
                    <div className="text-xl font-black text-blue-400 mt-0.5 tracking-tight flex items-baseline gap-1">
                      <span>{dailyEdges.total.gap.toFixed(1)} Runs</span>
                      <span className="text-[10px] text-gray-400 font-bold">Diff</span>
                    </div>
                  </div>
                  <div className="mt-3 flex justify-between items-center text-[9px] text-gray-400 border-t border-slate-900/60 pt-2">
                    <span className="font-semibold text-slate-400">Proj Total: {dailyEdges.total.modelTotal.toFixed(1)}</span>
                    <span className="text-slate-500 group-hover:text-blue-400 font-black transition-colors uppercase tracking-widest">Analyze →</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ================= MODEL TOGGLE BUTTONS ================= */}
        <div className="flex justify-center items-center gap-2 mb-8 bg-slate-900/60 p-2 rounded-xl border border-gray-800/80 max-w-lg mx-auto">
          <button
            onClick={() => setActiveModel('full')}
            className={`flex-1 py-2 px-4 rounded-lg text-xs font-black uppercase tracking-widest transition-all duration-300 ${activeModel === 'full'
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50'
              : 'text-gray-400 hover:text-gray-200 hover:bg-slate-800'
              }`}
          >
            Daily Games
          </button>
          <button
            onClick={() => setActiveModel('nrfi')}
            className={`flex-1 py-2 px-4 rounded-lg text-xs font-black uppercase tracking-widest transition-all duration-300 ${activeModel === 'nrfi'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-900/50'
              : 'text-gray-400 hover:text-gray-200 hover:bg-slate-800'
              }`}
          >
            NRFI Model
          </button>
        </div>

        {/* ================= KARTLARIN OLDUĞU BÖLÜM ================= */}
        <div className="grid grid-cols-1 gap-4">
          {loading ? (
            <>
              <MatchupSkeleton />
              <MatchupSkeleton />
              <MatchupSkeleton />
            </>
          ) : predictions.length === 0 ? (
            /* Empty State Entegrasyonu */
            <div className="bg-slate-900 border border-dashed border-gray-700 rounded-xl p-10 text-center my-6 shadow-inner">
              <span className="text-5xl block mb-4" role="img" aria-label="baseball">⚾</span>
              <h3 className="text-lg font-black text-white uppercase tracking-wider mb-2">
                No Games Scheduled Today
              </h3>
              <p className="text-gray-400 text-sm max-w-md mx-auto font-medium">
                There are no active MLB matchups processed by the engine for {systemDate || 'today'}. This might be due to a league rest day or game postponements.
              </p>
            </div>
          ) : (
            displayPredictions.map((game, idx) => (
              activeModel === 'full' ? (
                <MatchupCard
                  key={`full-${game.matchup.away_team}-${game.matchup.home_team}-${idx}`}
                  prediction={game}
                  onNavigateToNrfi={() => onNavigateToNrfi(`${game.matchup.away_team}-${game.matchup.home_team}`)}
                />
              ) : (
                <NrfiRow
                  key={`nrfi-${game.matchup.away_team}-${game.matchup.home_team}-${idx}`}
                  prediction={game}
                />
              )
            ))
          )}
        </div>

        <Footer />
      </main>

      {/* Floating Back to Top Button */}
      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-6 right-6 z-50 p-3 md:p-3.5 bg-indigo-600/90 hover:bg-indigo-500 text-white rounded-full shadow-[0_4px_20px_rgba(99,102,241,0.4)] border border-indigo-400/30 hover:scale-110 active:scale-95 transition-all duration-300 backdrop-blur-md cursor-pointer group flex items-center justify-center animate-fade-in"
          aria-label="Scroll to top"
        >
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            fill="none" 
            viewBox="0 0 24 24" 
            strokeWidth={3} 
            stroke="currentColor" 
            className="w-5 h-5 group-hover:-translate-y-0.5 transition-transform duration-300"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18" />
          </svg>
        </button>
      )}
    </div>
  );
}

export default App;