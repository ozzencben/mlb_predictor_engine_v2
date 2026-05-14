import React from 'react';

const MatchupSkeleton = () => {
    return (
        <div className="bg-mlb-card rounded-xl border border-gray-800 shadow-2xl overflow-hidden mb-8 w-full animate-pulse">

            {/* 1. ÜST BAR SKELETON */}
            <div className="bg-slate-800/50 px-4 py-3 flex justify-between items-center border-b border-gray-700/50">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-4 bg-slate-700 rounded"></div>
                    <div className="w-32 h-3 bg-slate-700 rounded"></div>
                </div>
                <div className="w-12 h-6 bg-slate-700 rounded-md"></div>
            </div>

            {/* 2. ANA KART İÇERİĞİ */}
            <div className="p-4 md:p-6">
                <div className="flex w-full justify-between items-start mb-6">

                    {/* SOL TAKIM SKELETON */}
                    <div className="w-[35%] flex flex-col items-center">
                        <div className="w-16 h-16 md:w-20 md:h-20 bg-slate-800 rounded-full mb-3"></div>
                        <div className="w-20 h-4 bg-slate-800 rounded mb-2"></div>
                        <div className="w-24 h-10 bg-slate-800/80 rounded-lg"></div>
                    </div>

                    {/* ORTA SAAT SKELETON */}
                    <div className="w-[30%] flex flex-col items-center pt-4">
                        <div className="w-12 h-2 bg-slate-800 rounded mb-2"></div>
                        <div className="w-16 h-6 bg-slate-800 rounded-full"></div>
                    </div>

                    {/* SAĞ TAKIM SKELETON */}
                    <div className="w-[35%] flex flex-col items-center">
                        <div className="w-16 h-16 md:w-20 md:h-20 bg-slate-800 rounded-full mb-3"></div>
                        <div className="w-20 h-4 bg-slate-800 rounded mb-2"></div>
                        <div className="w-24 h-10 bg-slate-800/80 rounded-lg"></div>
                    </div>
                </div>

                {/* ORTA SKOR/WIN PROB SKELETON */}
                <div className="flex flex-col items-center gap-4 mt-4">
                    <div className="w-32 h-10 bg-slate-800 rounded-xl"></div>
                    <div className="w-48 h-2 bg-slate-800 rounded-full"></div>
                    <div className="w-56 h-12 bg-slate-800/60 rounded-xl"></div>
                </div>

                {/* BUTONLAR SKELETON */}
                <div className="mt-8 pt-4 border-t border-slate-700/50 flex justify-between items-center">
                    <div className="w-20 h-4 bg-slate-800 rounded"></div>
                    <div className="w-24 h-9 bg-slate-800 rounded-lg"></div>
                </div>
            </div>
        </div>
    );
};

export default MatchupSkeleton;