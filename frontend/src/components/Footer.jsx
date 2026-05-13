import React from 'react';

const Footer = () => {
    return (
        <footer className="w-full py-6 mt-8 border-t border-slate-800/50 bg-slate-900/30">
            <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4">

                {/* Sol Kısım: Proje İsmi ve Versiyon */}
                <div className="text-center md:text-left">
                    <p className="text-xs text-gray-500 font-bold uppercase tracking-widest">
                        MLB Predictive Engine <span className="text-mlb-green ml-1">v2.0</span>
                    </p>
                    <p className="text-[10px] text-gray-600 mt-1">
                        Advanced Sabermetrics & Value Betting Algorithm
                    </p>
                </div>

                {/* Sağ Kısım: Senin İmzan (Zarif ve Tıklanabilir) */}
                <div className="text-center md:text-right flex flex-col items-center md:items-end">
                    <p className="text-[10px] text-gray-600 font-medium uppercase tracking-wider mb-1">
                        Engineered & Developed By
                    </p>
                    <div className="flex items-center gap-3">
                        <a
                            href="mailto:ozzencben@gmail.com"
                            className="text-xs text-gray-400 hover:text-blue-400 transition-colors font-semibold"
                            title="Send an Email"
                        >
                            Ozenc
                        </a>
                        <span className="text-gray-700 text-xs">|</span>
                        <a
                            href="https://www.upwork.com/freelancers/~01bd880efba1b95a83"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-gray-400 hover:text-green-400 transition-colors font-semibold flex items-center gap-1"
                            title="View Upwork Profile"
                        >
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24"><path d="M17.48 6.07c-2.45 0-4.08 1.56-4.66 3.65l-.33-1.64H9.6v6.86h2.89v-3.79c0-1.8.84-2.88 2.21-2.88 1.48 0 2.21 1.09 2.21 2.88v3.79h2.89v-3.84c0-2.85-1.57-5.03-4.32-5.03zM5.59 13.06c-1.63 0-2.7-1.15-2.7-2.85V6.07H0v4.14c0 3.32 2.3 5.76 5.59 5.76 3.28 0 5.58-2.44 5.58-5.76V6.07H8.28v4.14c0 1.7-1.07 2.85-2.69 2.85z" /></svg>
                            Upwork Profile
                        </a>
                    </div>
                </div>

            </div>
        </footer>
    );
};

export default Footer;