import React from 'react';

function DropdownNavigation({
  activeModel,
  setActiveModel,
  lastUpdated,
  loading,
  menuOpen,
  setMenuOpen
}) {
  if (!menuOpen) return null;

  return (
    <>
      {/* Backdrop overlay to close menu on click outside */}
      <div 
        className="fixed inset-0 z-40 bg-black/10 backdrop-blur-[1px] md:backdrop-blur-none cursor-default"
        onClick={() => setMenuOpen(false)}
      />

      {/* Dropdown Menu Container */}
      <div className="absolute right-0 top-16 z-50 w-64 rounded-2xl border border-slate-800 bg-slate-900/95 p-4 shadow-2xl backdrop-blur-xl animate-fade-in origin-top-right transition-all duration-300 border-t border-t-indigo-500/30">
        <div className="space-y-1">
          <span className="text-[10px] text-slate-500 font-black uppercase tracking-[0.2em] px-2 block mb-1">
            Navigation
          </span>
          
          <button
            onClick={() => {
              setActiveModel('full');
              setMenuOpen(false);
            }}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all duration-200 text-left ${
              activeModel === 'full'
                ? 'bg-blue-600/20 border border-blue-500/30 text-blue-400 font-extrabold shadow-[0_0_15px_rgba(59,130,246,0.1)]'
                : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800/50 border border-transparent'
            }`}
          >
            <span className="text-base leading-none">⚾</span>
            <span>Daily Predictions</span>
          </button>

          <button
            onClick={() => {
              setActiveModel('nrfi');
              setMenuOpen(false);
            }}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all duration-200 text-left ${
              activeModel === 'nrfi'
                ? 'bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 font-extrabold shadow-[0_0_15px_rgba(99,102,241,0.1)]'
                : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800/50 border border-transparent'
            }`}
          >
            <span className="text-base leading-none">📈</span>
            <span>NRFI Model</span>
          </button>

          <button
            onClick={() => {
              setActiveModel('pitcher_props');
              setMenuOpen(false);
            }}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all duration-200 text-left ${
              activeModel === 'pitcher_props'
                ? 'bg-cyan-600/20 border border-cyan-500/30 text-cyan-400 font-extrabold shadow-[0_0_15px_rgba(6,182,212,0.1)]'
                : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800/50 border border-transparent'
            }`}
          >
            <span className="text-base leading-none">🎯</span>
            <span>Pitcher Projections</span>
          </button>
        </div>

        {/* Separator */}
        <div className="my-3 border-t border-slate-800/80" />

        {/* System Info Block */}
        <div className="space-y-3 px-2">
          {/* Status */}
          <div>
            <span className="text-[10px] text-slate-500 font-black uppercase tracking-[0.2em] block mb-1">
              System Status
            </span>
            <div className="flex items-center gap-2">
              <div className="relative flex h-2 w-2">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${loading ? 'bg-amber-400' : 'bg-green-400'}`}></span>
                <span className={`relative inline-flex rounded-full h-2 w-2 ${loading ? 'bg-amber-500' : 'bg-green-500'}`}></span>
              </div>
              <span className={`text-[11px] font-black uppercase tracking-wider ${loading ? 'text-amber-500' : 'text-green-500'}`}>
                {loading ? 'Syncing...' : 'Live & Ready'}
              </span>
            </div>
          </div>

          {/* Last Update */}
          {lastUpdated && (
            <div>
              <span className="text-[10px] text-slate-500 font-black uppercase tracking-[0.2em] block mb-0.5">
                Last Update
              </span>
              <span className="text-[11px] text-slate-300 font-extrabold tracking-tight block truncate">
                {lastUpdated}
              </span>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default DropdownNavigation;
