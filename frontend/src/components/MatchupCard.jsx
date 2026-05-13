import React from 'react';
import { formatAmericanOdds, getTeamLogo } from '../utils/formatters';

const MatchupCard = ({ prediction }) => {
    const { matchup, NRFI, F5, Full_Game, Odds } = prediction;

    return (
        <div className="bg-mlb-card rounded-xl border border-gray-700 shadow-2xl overflow-hidden mb-6 transition-all duration-300 hover:border-gray-500">
            {/* Üst Bar: Takım İsimleri ve Lig Bilgisi */}
            <div className="bg-slate-800/80 px-3 md:px-4 py-2 flex justify-between items-center text-[10px] md:text-xs text-gray-400 font-bold uppercase tracking-wider">
                <span className="truncate pr-2">{matchup.away_team} @ {matchup.home_team}</span>
                <span className="bg-blue-600/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded flex-shrink-0">MLB</span>
            </div>

            <div className="p-4 md:p-6">
                {/* MOBİLDE: flex-wrap ile alt alta geçer. MASAÜSTÜNDE: flex-nowrap ile yan yana durur */}
                <div className="flex flex-wrap md:flex-nowrap items-start md:items-center justify-between">

                    {/* 1. Deplasman Takımı (Mobilde Sol - w-1/2) */}
                    <div className="flex flex-col items-center w-1/2 md:w-1/3 order-1 text-center px-1">
                        <img src={getTeamLogo(matchup.away_team)} alt={matchup.away_team} className="w-14 h-14 md:w-16 md:h-16 mb-2 drop-shadow-lg" />
                        <h2 className="text-base md:text-xl font-black leading-tight">{matchup.away_team}</h2>
                        <p className="text-[9px] md:text-[10px] text-gray-400 mt-1 truncate w-full px-2">{matchup.away_pitcher}</p>
                    </div>

                    {/* 2. Ev Sahibi Takımı (Mobilde Sağ - w-1/2) */}
                    <div className="flex flex-col items-center w-1/2 md:w-1/3 order-2 md:order-3 text-center px-1">
                        <img src={getTeamLogo(matchup.home_team)} alt={matchup.home_team} className="w-14 h-14 md:w-16 md:h-16 mb-2 drop-shadow-lg" />
                        <h2 className="text-base md:text-xl font-black leading-tight">{matchup.home_team}</h2>
                        <p className="text-[9px] md:text-[10px] text-gray-400 mt-1 truncate w-full px-2">{matchup.home_pitcher}</p>
                    </div>

                    {/* 3. Orta Alan: Skor Tahmini ve Oranlar (Mobilde Alt Satır - w-full) */}
                    {/* order-3 ile mobilde en alta atıyoruz, md:order-2 ile masaüstünde ortaya alıyoruz */}
                    <div className="flex flex-col items-center w-full md:w-1/3 order-3 md:order-2 mt-6 md:mt-0 pt-5 md:pt-0 border-t border-gray-700/50 md:border-0">

                        {/* Win Probability Boxes */}
                        <div className="flex items-center gap-3 mb-3">
                            <div className="bg-slate-700/50 border border-slate-600 px-3 py-1 rounded text-sm md:text-lg font-black text-gray-200">
                                {Math.round(Full_Game.full_away_win_prob * 100)}%
                            </div>
                            <div className="text-lg md:text-xl font-black text-gray-500 italic">vs</div>
                            <div className="bg-slate-700/50 border border-slate-600 px-3 py-1 rounded text-sm md:text-lg font-black text-gray-200">
                                {Math.round(Full_Game.full_home_win_prob * 100)}%
                            </div>
                        </div>

                        {/* O/U Barem & Oranlar (Covers Stili Kutu İçinde) */}
                        <div className="bg-slate-900/50 border border-slate-700/50 rounded-lg px-4 py-2 w-full max-w-[200px] flex flex-col items-center">
                            <div className="text-gray-400 text-[10px] md:text-xs font-bold uppercase tracking-widest mb-1">
                                Total O/U: <span className="text-white">{Full_Game.full_total}</span>
                            </div>
                            <div className="flex justify-between w-full px-2 mt-1">
                                <span className={`text-sm md:text-base font-black ${Odds.away_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-300'}`}>
                                    {formatAmericanOdds(Odds.best_away_odds)}
                                </span>
                                <span className="text-gray-600 font-light">|</span>
                                <span className={`text-sm md:text-base font-black ${Odds.home_edge_pct > 5 ? 'text-mlb-green' : 'text-gray-300'}`}>
                                    {formatAmericanOdds(Odds.best_home_odds)}
                                </span>
                            </div>
                        </div>

                    </div>
                </div>

                {/* Alt Bilgi: NRFI ve Value Bildirimi (Mobilde alt alta geçebilen yapı) */}
                <div className="mt-5 md:mt-6 pt-4 border-t border-gray-700/50 flex flex-col sm:flex-row justify-between items-center gap-3 sm:gap-0">

                    <div className="text-xs flex items-center bg-gray-800/50 px-3 py-1.5 rounded-md border border-gray-700">
                        <span className="text-gray-400 font-bold uppercase tracking-wider text-[10px]">Model Pick:</span>
                        <span className={`ml-2 px-2 py-0.5 rounded font-black tracking-wide ${NRFI.pick === 'NRFI' ? 'bg-blue-900/40 text-blue-400 border border-blue-800/50' : 'bg-red-900/40 text-red-400 border border-red-800/50'}`}>
                            {NRFI.pick} ({Math.round(NRFI.confidence * 100)}%)
                        </span>
                    </div>

                    {(Odds.away_edge_pct > 5 || Odds.home_edge_pct > 5) && (
                        <div className="animate-pulse flex items-center bg-green-900/20 border border-mlb-green/40 px-3 py-1.5 rounded-md shadow-[0_0_10px_rgba(34,197,94,0.1)]">
                            <span className="text-mlb-green text-[10px] md:text-xs font-black uppercase tracking-wider flex items-center gap-1">
                                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd"></path></svg>
                                High Value Detected
                            </span>
                        </div>
                    )}
                </div>

            </div>
        </div>
    );
};

export default MatchupCard;