import React, { useState } from 'react';

function TennisDashboard() {
    const [selectedTournament, setSelectedTournament] = useState('all');

    // Mock tenis maç tahminleri listesi
    const tennisPredictions = [
        {
            id: 1,
            tournament: 'Wimbledon (Grand Slam)',
            matchup: 'Carlos Alcaraz vs Jannik Sinner',
            round: 'Quarter-Finals',
            status: 'TODAY 15:30 EST',
            odds: { player1: -120, player2: +105, player1_edge: '+6.2%', player2_edge: 'PASS' },
            model: { player1_win_prob: '57%', player2_win_prob: '43%', value_pick: 'Alcaraz ML' },
            surface: 'Grass'
        },
        {
            id: 2,
            tournament: 'Wimbledon (Grand Slam)',
            matchup: 'Iga Swiatek vs Aryna Sabalenka',
            round: 'Semi-Finals',
            status: 'TODAY 13:00 EST',
            odds: { player1: -145, player2: +125, player1_edge: 'PASS', player2_edge: '+4.8%' },
            model: { player1_win_prob: '54%', player2_win_prob: '46%', value_pick: 'Sabalenka +1.5 Sets' },
            surface: 'Grass'
        },
        {
            id: 3,
            tournament: 'Wimbledon (Grand Slam)',
            matchup: 'Novak Djokovic vs Daniil Medvedev',
            round: 'Quarter-Finals',
            status: 'TOMORROW 14:00 EST',
            odds: { player1: -160, player2: +135, player1_edge: '+5.4%', player2_edge: 'PASS' },
            model: { player1_win_prob: '65%', player2_win_prob: '35%', value_pick: 'Djokovic ML' },
            surface: 'Grass'
        },
        {
            id: 4,
            tournament: 'WTA Eastbourne',
            matchup: 'Coco Gauff vs Ons Jabeur',
            round: 'Finals',
            status: 'TOMORROW 11:30 EST',
            odds: { player1: -110, player2: -110, player1_edge: 'PASS', player2_edge: '+3.1%' },
            model: { player1_win_prob: '48%', player2_win_prob: '52%', value_pick: 'Jabeur ML' },
            surface: 'Grass'
        }
    ];

    const filteredPredictions = selectedTournament === 'all'
        ? tennisPredictions
        : tennisPredictions.filter(p => p.tournament.toLowerCase().includes(selectedTournament));

    return (
        <div className="space-y-8 animate-fade-in pb-10">
            {/* Üst Bilgi Başlığı (BETA Rozeti ile) */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/40 border border-slate-850 p-5 sm:p-6 rounded-3xl backdrop-blur-xl relative overflow-hidden border-t-indigo-500/20">
                <div className="absolute top-0 right-0 w-48 h-48 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none"></div>
                <div className="space-y-1.5 relative z-10 text-center md:text-left">
                    <div className="flex items-center justify-center md:justify-start gap-2.5 flex-wrap">
                        <span className="text-2xl sm:text-3xl">🎾</span>
                        <h2 className="text-lg sm:text-xl md:text-2xl font-black text-white uppercase tracking-wider">
                            Tennis Match Projections
                        </h2>
                        <span className="text-[9px] font-black tracking-widest text-cyan-400 bg-cyan-950/50 border border-cyan-500/30 px-2 py-0.5 rounded-md uppercase">
                            BETA
                        </span>
                    </div>
                    <p className="text-xs text-slate-400 font-semibold max-w-2xl leading-relaxed mx-auto md:mx-0">
                        Markov chain-based point simulator. Calculating tennis matchups point-by-point to generate game totals, set spreads, and moneyline edges.
                    </p>
                </div>

                <div className="flex items-center justify-center md:justify-end gap-2 border border-slate-850 bg-slate-950/50 p-1.5 rounded-xl self-center md:self-auto">
                    <button
                        onClick={() => setSelectedTournament('all')}
                        className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all cursor-pointer ${selectedTournament === 'all' ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/20' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                        All
                    </button>
                    <button
                        onClick={() => setSelectedTournament('wimbledon')}
                        className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all cursor-pointer ${selectedTournament === 'wimbledon' ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/20' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                        Wimbledon
                    </button>
                </div>
            </div>

            {/* Maç Tahmin Kartları Izgarası */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {filteredPredictions.map(predict => (
                    <div
                        key={predict.id}
                        className="bg-slate-900/30 border border-slate-850 rounded-3xl p-5 hover:border-slate-800 transition-all duration-300 flex flex-col justify-between gap-5 relative overflow-hidden"
                    >
                        {/* Turnuva Bilgisi */}
                        <div className="flex justify-between items-center border-b border-slate-950 pb-3">
                            <div className="flex flex-col">
                                <span className="text-[10px] text-indigo-400 font-black uppercase tracking-wider">{predict.tournament}</span>
                                <span className="text-[9px] text-slate-500 font-bold">{predict.round} • {predict.surface} Court</span>
                            </div>
                            <span className="text-[10px] text-cyan-400 font-black bg-cyan-950/20 border border-cyan-500/15 px-2 py-0.5 rounded-md">
                                {predict.status}
                            </span>
                        </div>

                        {/* Oyuncular ve Olasılıklar */}
                        <div className="grid grid-cols-5 gap-3 items-center my-1">
                            <div className="col-span-2 text-left space-y-1">
                                <span className="text-xs font-black text-gray-200 block truncate">{predict.matchup.split(' vs ')[0]}</span>
                                <span className="text-[10px] text-slate-500 font-bold">Odds: {predict.odds.player1 > 0 ? `+${predict.odds.player1}` : predict.odds.player1}</span>
                            </div>
                            <div className="col-span-1 text-center flex flex-col items-center justify-center">
                                <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">vs</span>
                                <div className="h-6 w-[1px] bg-slate-950 my-1"></div>
                            </div>
                            <div className="col-span-2 text-right space-y-1">
                                <span className="text-xs font-black text-gray-200 block truncate">{predict.matchup.split(' vs ')[1]}</span>
                                <span className="text-[10px] text-slate-500 font-bold">Odds: {predict.odds.player2 > 0 ? `+${predict.odds.player2}` : predict.odds.player2}</span>
                            </div>
                        </div>

                        {/* Model Çıktıları */}
                        <div className="grid grid-cols-2 gap-4 bg-slate-950/60 border border-slate-900 rounded-2xl p-3.5 shadow-inner">
                            <div className="border-r border-slate-900 space-y-1 pl-1">
                                <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Win Probability</span>
                                <div className="flex items-center gap-2 text-xs font-black text-gray-300">
                                    <span>{predict.model.player1_win_prob}</span>
                                    <span className="text-[9px] text-slate-500 font-bold">vs</span>
                                    <span>{predict.model.player2_win_prob}</span>
                                </div>
                            </div>
                            <div className="space-y-1 pl-3">
                                <span className="text-[8px] text-slate-500 font-black uppercase tracking-wider block">Consensus Pick</span>
                                <div className="text-xs font-black text-indigo-400 flex items-center gap-1.5">
                                    <span>🎯 {predict.model.value_pick}</span>
                                    {predict.odds.player1_edge !== 'PASS' && (
                                        <span className="text-[8px] text-emerald-400 bg-emerald-950/40 px-1 py-0.2 rounded border border-emerald-500/20">{predict.odds.player1_edge} Edge</span>
                                    )}
                                    {predict.odds.player2_edge !== 'PASS' && (
                                        <span className="text-[8px] text-emerald-400 bg-emerald-950/40 px-1 py-0.2 rounded border border-emerald-500/20">{predict.odds.player2_edge} Edge</span>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Alt Bilgi */}
                        <div className="flex justify-between items-center text-[9px] text-slate-500 border-t border-slate-950 pt-3">
                            <span>Recursion Depth: 10,000 simulations</span>
                            <span className="font-extrabold uppercase text-indigo-500 tracking-wider">Markov Model Active</span>
                        </div>
                    </div>
                ))}
            </div>

            {/* Model Açıklaması */}
            <div className="bg-slate-900/40 border border-slate-850 rounded-3xl p-6 relative overflow-hidden">
                <h4 className="text-xs font-black text-white uppercase tracking-wider mb-2.5">Tennis Markov Chain Process</h4>
                <p className="text-xs text-slate-400 leading-relaxed font-semibold">
                    Unlike standard regression models, our Tennis engine models match progression dynamically. By defining each player's serve-win-probability against their opponent's return rating, we calculate state transitions for each game, set, and match outcome. This allows us to find high-value discrepancies against bookmaker odds on spreads and totals.
                </p>
            </div>
        </div>
    );
}

export default TennisDashboard;
