import React, { useState } from 'react';
import { usePredictions } from './hooks/usePredictions';
import MatchupCard from './components/MatchupCard';
import MatchupSkeleton from './components/MatchupSkeleton';
import Footer from './components/Footer';
import NrfiRow from './components/NrfiRow';
import logo2Img from './assets/logo2.png';

function App() {
  const [activeModel, setActiveModel] = useState('full'); // 'full', 'nrfi', 'f5'
  const { data, loading, error, isPreparing } = usePredictions();

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
    </div>
  );
}

export default App;