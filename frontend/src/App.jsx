import React, { useState } from 'react';
import { usePredictions } from './hooks/usePredictions';
import MatchupCard from './components/MatchupCard';
import MatchupSkeleton from './components/MatchupSkeleton';
import Footer from './components/Footer';
import NrfiRow from './components/NrfiRow';

function App() {
  const [activeModel, setActiveModel] = useState('full'); // 'full', 'nrfi', 'f5'
  const { data, loading, error } = usePredictions();

  if (error) return <div className="p-10 text-red-500 text-center font-black">❌ Connection Error: {error}</div>;

  const predictions = data?.data?.predictions || [];
  const systemDate = data?.data?.date || '';
  const lastUpdated = data?.data?.last_updated;

  // Sort NRFI predictions from highest AI score to least when active
  const displayPredictions = activeModel === 'nrfi'
    ? [...predictions].sort((a, b) => (b.NRFI?.confidence || 0) - (a.NRFI?.confidence || 0))
    : predictions;

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8">
      {/* ================= HEADER ================= */}
      <header className="mb-10 flex flex-col md:flex-row justify-between items-end border-b border-gray-800 pb-6">
        <div>
          <h1 className="text-4xl font-black text-white italic tracking-tighter">
            TYLER MLB <span className="text-blue-500">PREDICTOR</span>
          </h1>
          <p className="text-gray-500 text-sm font-bold tracking-tight">
            Data-Driven Insights for {loading ? 'Loading...' : systemDate || 'No Date'}
          </p>
        </div>

        <div className="mt-4 md:mt-0 text-right">
          {!loading && lastUpdated && (
            <div className="mb-1">
              <span className="text-[9px] text-gray-600 font-black uppercase tracking-[0.2em]">
                Last Update: <span className="text-gray-400">{lastUpdated}</span>
              </span>
            </div>
          )}

          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">
            System Status
          </span>
          <div className="flex items-center justify-end gap-2 mt-0.5">
            <div className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </div>
            <span className="text-xs font-bold text-green-500 uppercase tracking-tighter">
              {loading ? 'Syncing...' : 'Live & Ready'}
            </span>
          </div>
        </div>
      </header>

      {/* ================= MODEL TOGGLE BUTTONS ================= */}
      <div className="flex justify-center items-center gap-2 mb-8 bg-slate-900/60 p-2 rounded-xl border border-gray-800/80 max-w-lg mx-auto">
        <button
          onClick={() => setActiveModel('full')}
          className={`flex-1 py-2 px-4 rounded-lg text-xs font-black uppercase tracking-widest transition-all duration-300 ${
            activeModel === 'full' 
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' 
              : 'text-gray-500 hover:text-gray-300 hover:bg-slate-800'
          }`}
        >
          Daily Games
        </button>
        <button
          onClick={() => setActiveModel('nrfi')}
          className={`flex-1 py-2 px-4 rounded-lg text-xs font-black uppercase tracking-widest transition-all duration-300 ${
            activeModel === 'nrfi' 
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-900/50' 
              : 'text-gray-500 hover:text-gray-300 hover:bg-slate-800'
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
          displayPredictions.map((game) => (
            activeModel === 'full' ? (
              <MatchupCard 
                key={`${game.matchup.away_team}-${game.matchup.home_team}`} 
                prediction={game} 
              />
            ) : (
              <NrfiRow 
                key={`${game.matchup.away_team}-${game.matchup.home_team}`} 
                prediction={game} 
              />
            )
          ))
        )}
      </div>

      <Footer />
    </div>
  );
}

export default App;