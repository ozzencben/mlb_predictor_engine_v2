import React from 'react';
import logo2Img from '../assets/logo2.png';

const Footer = ({ setShowAboutModal, setShowContactModal, setShowDisclaimerModal }) => {
    return (
        <footer className="w-full py-10 mt-12 border-t border-slate-900 bg-slate-950/60 backdrop-blur-md">
            <div className="max-w-5xl mx-auto px-4 flex flex-col items-center gap-8 text-center">

                {/* Sleek Side-by-Side Cards (Vemno Donation & Contact Us) */}
                <div className="footer-cards-grid gap-6 w-full items-stretch">
                    
                    {/* Sleek Venmo Donation Card */}
                    <div className="bg-gradient-to-b from-blue-950/20 to-slate-950/40 border border-blue-900/35 rounded-2xl p-6 flex flex-col items-center justify-between gap-6 shadow-lg shadow-black/30 w-full text-center">
                        <div className="flex flex-col items-center gap-3.5">
                            <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center text-2xl shadow-[0_0_15px_rgba(59,130,246,0.2)] flex-shrink-0">
                                💙
                            </div>
                            <div className="space-y-1.5">
                                <h4 className="text-xs sm:text-sm font-black text-white uppercase tracking-wider">Like this site?</h4>
                                <p className="text-[10px] sm:text-xs text-slate-400 font-medium max-w-sm leading-relaxed">
                                    A donation from Venmo will help keep my web pages maintained. Any amount is appreciated. Thank you!
                                </p>
                            </div>
                        </div>
                        <a
                            href="https://venmo.com/lgds_brand"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="w-full bg-[#008CFF] hover:bg-[#007cd6] text-white text-[10px] sm:text-xs font-black uppercase tracking-widest py-3 rounded-xl transition-all duration-300 shadow-md shadow-blue-500/15 hover:scale-[1.02] active:scale-[0.98] text-center"
                        >
                            Donate via Venmo
                        </a>
                    </div>

                    {/* 1. Contact Us Card */}
                    <div className="bg-slate-900/30 border border-slate-900 rounded-2xl p-6 flex flex-col justify-between gap-5 w-full shadow-inner text-left">
                        <div className="space-y-4">
                            {/* Contact Us Header */}
                            <div className="flex items-center gap-2.5">
                                <img src={logo2Img} alt="Legends Sports" className="h-8 w-auto object-contain rounded" />
                                <div>
                                    <h4 className="text-xs sm:text-sm font-black text-white uppercase tracking-wider">Contact Us</h4>
                                    <p className="text-[9px] sm:text-[10px] text-slate-500 font-bold">Get in touch with the Legends Sports team</p>
                                </div>
                            </div>

                            {/* Issue bubble */}
                            <div className="bg-emerald-950/10 border border-emerald-500/10 rounded-xl p-3 flex gap-2.5">
                                <svg className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v5.03Z" />
                                </svg>
                                <div>
                                    <h5 className="text-[10px] font-bold text-emerald-400">Have an issue or question?</h5>
                                    <p className="text-[9px] text-slate-400 mt-1 leading-relaxed">
                                        We'd love to hear from you! Whether you've found a bug, have a feature request, or just want to share feedback about Legends Sports, please don't hesitate to reach out.
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Email display (No open/copy buttons as requested) */}
                        <div className="bg-slate-950/60 border border-slate-900 rounded-xl p-3 text-center">
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center justify-center gap-1.5">
                                <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
                                </svg>
                                Email Us
                            </span>
                            <div className="bg-white rounded-lg py-2 px-3 mt-2 select-all shadow-inner">
                                <span className="text-slate-950 font-extrabold text-[11px] sm:text-xs tracking-wide">
                                    legendsbrandcompany@gmail.com
                                </span>
                            </div>
                        </div>
                    </div>

                </div>

                {/* Footer Navigation Links */}
                <div className="flex flex-wrap justify-center items-center gap-4 text-[10px] font-black uppercase tracking-wider text-slate-500 mt-2 select-none">
                    <button onClick={() => setShowAboutModal?.(true)} className="hover:text-cyan-400 cursor-pointer transition-colors">About Us</button>
                    <span className="text-slate-800">|</span>
                    <button onClick={() => setShowContactModal?.(true)} className="hover:text-cyan-400 cursor-pointer transition-colors">Contact Us</button>
                    <span className="text-slate-800">|</span>
                    <button onClick={() => setShowDisclaimerModal?.(true)} className="hover:text-cyan-400 cursor-pointer transition-colors">Terms & Disclaimer</button>
                </div>

                {/* 2. Liability Disclaimer (Second) */}
                <div className="border-t border-slate-900/60 pt-6 w-full flex flex-col items-center">
                    <p className="text-[10px] sm:text-xs text-slate-500 leading-relaxed text-center max-w-2xl font-medium">
                        Legends Sports cannot be held liable for any losses incurred. These tools provide data-driven insights only and do not constitute financial or gambling advice. Please bet responsibly. By using Legends Sports, you confirm you are of legal betting age in your jurisdiction.
                    </p>
                </div>

                {/* 3. 21+ circular badge & Gambling problem message (Last) */}
                <div className="flex items-center gap-3 bg-slate-900/20 border border-slate-900 rounded-xl p-3 w-fit">
                    <div className="border-2 border-red-500/80 rounded-full w-8 h-8 flex items-center justify-center text-[10px] font-black text-red-500 flex-shrink-0">
                        21+
                    </div>
                    <div className="text-[10px] sm:text-xs font-semibold text-slate-400 leading-tight text-left">
                        <p>Gambling Problem?</p>
                        <p className="text-slate-500">Call 1-800-522-4700</p>
                    </div>
                </div>

                {/* Bottom Signature Row */}
                <div className="w-full flex flex-col md:flex-row items-center justify-between gap-4 border-t border-slate-900 pt-6 text-[10px] text-slate-600">
                    <p className="font-bold uppercase tracking-wider text-center md:text-left">
                        © {new Date().getFullYear()} Legends Sports. All Rights Reserved.
                    </p>

                    <div className="text-center md:text-right flex flex-col items-center md:items-end">
                        <p className="font-bold uppercase tracking-wider mb-1">
                            Engineered & Developed By
                        </p>
                        <div className="flex items-center gap-3">
                            <a
                                href="mailto:ozzencben@gmail.com"
                                className="text-[11px] text-slate-500 hover:text-cyan-400 transition-colors font-bold uppercase tracking-wide"
                                title="Send an Email"
                            >
                                Ozenc
                            </a>
                            <span className="text-slate-800 text-xs">|</span>
                            <a
                                href="https://www.upwork.com/freelancers/~01bd880efba1b95a83"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[11px] text-slate-500 hover:text-emerald-400 transition-colors font-bold uppercase tracking-wide flex items-center gap-1"
                                title="View Upwork Profile"
                            >
                                <svg className="w-3 h-3 text-emerald-500/80" fill="currentColor" viewBox="0 0 24 24"><path d="M17.48 6.07c-2.45 0-4.08 1.56-4.66 3.65l-.33-1.64H9.6v6.86h2.89v-3.79c0-1.8.84-2.88 2.21-2.88 1.48 0 2.21 1.09 2.21 2.88v3.79h2.89v-3.84c0-2.85-1.57-5.03-4.32-5.03zM5.59 13.06c-1.63 0-2.7-1.15-2.7-2.85V6.07H0v4.14c0 3.32 2.3 5.76 5.59 5.76 3.28 0 5.58-2.44 5.58-5.76V6.07H8.28v4.14c0 1.7-1.07 2.85-2.69 2.85z" /></svg>
                                Upwork
                            </a>
                        </div>
                    </div>
                </div>

            </div>
        </footer>
    );
};

export default Footer;