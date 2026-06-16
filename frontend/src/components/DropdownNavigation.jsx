import React from 'react';
import { SPORTS_CONFIG } from '../utils/sports_config';

function DropdownNavigation({
    activeSport,
    setActiveSport,
    activeModel,
    setActiveModel,
    lastUpdated,
    loading,
    menuOpen,
    setMenuOpen,
    setShowAboutModal,
    setShowContactModal,
    setToastMessage
}) {
    if (!menuOpen) return null;

    const handleSportClick = (sportName, status, sportKey) => {
        if (status !== 'ACTIVE') {
            if (setToastMessage) {
                setToastMessage(status === 'BETA'
                    ? `${sportName} predictor is currently in Beta training and will be available soon!`
                    : `${sportName} predictor is currently in training and will be available soon!`);
            }
            return;
        }
        setActiveSport(sportKey.toLowerCase());
        setMenuOpen(false);
    };

    return (
        <>
            {/* Backdrop overlay to close menu on click outside */}
            <div
                className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm md:backdrop-blur-none cursor-default"
                onClick={() => setMenuOpen(false)}
            />

            {/* Dropdown Menu Container */}
            <div className="absolute right-0 top-16 z-50 w-72 rounded-2xl border border-slate-800 bg-slate-950/95 p-5 shadow-2xl backdrop-blur-xl animate-fade-in origin-top-right transition-all duration-300 border-t border-t-indigo-500/30">
                
                {/* Spor Dalları Seçimi */}
                <div className="space-y-1">
                    <span className="text-[10px] text-slate-500 font-black uppercase tracking-[0.2em] px-2 block mb-1">
                        Sports Predictors
                    </span>

                    {Object.entries(SPORTS_CONFIG).map(([key, sport]) => {
                        const isSelected = activeSport === sport.id;
                        const isComingSoon = sport.status === 'COMING_SOON';
                        const isBeta = sport.status === 'BETA';

                        return (
                            <div key={sport.id} className="flex flex-col">
                                <button
                                    onClick={() => handleSportClick(sport.name, sport.status, key)}
                                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all duration-200 text-left cursor-pointer ${
                                        isSelected
                                            ? 'bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 font-extrabold shadow-[0_0_15px_rgba(99,102,241,0.1)] border-t border-t-indigo-400/20'
                                            : 'text-slate-300 hover:text-slate-100 hover:bg-slate-900/50 border border-transparent'
                                    } ${isComingSoon ? 'opacity-50 hover:opacity-100' : ''}`}
                                >
                                    <span className="flex items-center gap-3">
                                        <span className="text-base leading-none">{sport.icon}</span>
                                        <span>{sport.name}</span>
                                    </span>
                                    {isBeta && (
                                        <span className="text-[8px] font-black tracking-widest text-cyan-400 bg-cyan-950/50 border border-cyan-500/30 px-1.5 py-0.5 rounded-md">
                                            BETA
                                        </span>
                                    )}
                                    {isComingSoon && (
                                        <span className="text-[8px] font-black tracking-widest text-slate-500 bg-slate-900/50 border border-slate-800 px-1.5 py-0.5 rounded-md">
                                            SOON
                                        </span>
                                    )}
                                </button>

                                {/* Eğer MLB aktifse alt modelleri de listele (Daha iyi UX) */}
                                {sport.id === 'mlb' && isSelected && (
                                    <div className="pl-8 pr-2 py-1.5 my-1 bg-slate-900/40 rounded-xl border border-slate-900 space-y-1">
                                        <button
                                            onClick={() => {
                                                setActiveModel('full');
                                                setMenuOpen(false);
                                            }}
                                            className={`w-full py-1.5 px-2 rounded-md text-[10px] font-bold uppercase tracking-wider text-left transition-all ${
                                                activeModel === 'full' ? 'text-blue-400 font-black' : 'text-slate-400 hover:text-slate-200'
                                            }`}
                                        >
                                            ⚾ Predictions
                                        </button>
                                        <button
                                            onClick={() => {
                                                setActiveModel('nrfi');
                                                setMenuOpen(false);
                                            }}
                                            className={`w-full py-1.5 px-2 rounded-md text-[10px] font-bold uppercase tracking-wider text-left transition-all ${
                                                activeModel === 'nrfi' ? 'text-indigo-400 font-black' : 'text-slate-400 hover:text-slate-200'
                                            }`}
                                        >
                                            📈 NRFI Model
                                        </button>
                                        <button
                                            onClick={() => {
                                                setActiveModel('pitcher_props');
                                                setMenuOpen(false);
                                            }}
                                            className={`w-full py-1.5 px-2 rounded-md text-[10px] font-bold uppercase tracking-wider text-left transition-all ${
                                                activeModel === 'pitcher_props' ? 'text-cyan-400 font-black' : 'text-slate-400 hover:text-slate-200'
                                            }`}
                                        >
                                            🎯 Pitchers
                                        </button>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Separator */}
                <div className="my-4 border-t border-slate-900" />

                {/* Bilgi Sayfaları */}
                <div className="space-y-1">
                    <span className="text-[10px] text-slate-500 font-black uppercase tracking-[0.2em] px-2 block mb-1">
                        Information
                    </span>
                    <button
                        onClick={() => {
                            setShowAboutModal(true);
                            setMenuOpen(false);
                        }}
                        className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-slate-100 hover:bg-slate-900/50 border border-transparent transition-all cursor-pointer text-left"
                    >
                        <span>ℹ️</span>
                        <span>About Legends</span>
                    </button>
                    <button
                        onClick={() => {
                            setShowContactModal(true);
                            setMenuOpen(false);
                        }}
                        className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-slate-100 hover:bg-slate-900/50 border border-transparent transition-all cursor-pointer text-left"
                    >
                        <span>✉️</span>
                        <span>Contact Us</span>
                    </button>
                </div>

                {/* Separator */}
                <div className="my-4 border-t border-slate-900" />

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
