import React from 'react';

/**
 * Intelligent utility to format the AI Insight strings, wrapping key sports analytics terms,
 * pitcher names, and weather markers in beautiful neon badges or colored span blocks,
 * and injecting mini responsive minimalist icons.
 */
export const formatAiInsight = (text) => {
    if (!text) return "No AI insight available for this matchup.";

    // Highlight Regex Patterns
    const patterns = [
        {
            regex: /\b(NRFI)\b/gi,
            replace: (match) => `<span class="bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded font-black text-[10px] md:text-xs tracking-wider uppercase inline-flex items-center gap-0.5 shadow-sm">⚾ ${match}</span>`
        },
        {
            regex: /\b(YRFI)\b/gi,
            replace: (match) => `<span class="bg-red-500/15 text-red-400 border border-red-500/20 px-1.5 py-0.5 rounded font-black text-[10px] md:text-xs tracking-wider uppercase inline-flex items-center gap-0.5 shadow-sm">🚨 ${match}</span>`
        },
        {
            regex: /\b(Under|Over)\b/gi,
            replace: (match) => `<span class="text-indigo-400 font-black">${match}</span>`
        },
        {
            regex: /\b(Vegas|Edge|confidence score|confidence|anomaly|anomalies|spread)\b/gi,
            replace: (match) => `<span class="text-amber-400 font-black">${match}</span>`
        },
        {
            regex: /\b(wind|wind blowing|temperature|humidity|weather|Red Flag)\b/gi,
            replace: (match) => `<span class="text-cyan-400 font-extrabold">💨 ${match}</span>`
        },
        // Match numbers with percentages like "75%", "66.7%"
        {
            regex: /(\d+(?:\.\d+)?%)/g,
            replace: (match) => `<span class="text-emerald-400 font-extrabold bg-emerald-500/5 px-1 py-0.5 rounded">${match}</span>`
        }
    ];

    let formattedHTML = text;
    patterns.forEach(({ regex, replace }) => {
        formattedHTML = formattedHTML.replace(regex, replace);
    });

    // Replace linebreaks/bulletpoints nicely
    formattedHTML = formattedHTML.replace(/-\s+/g, '<span class="text-indigo-500 mr-1.5 font-bold">•</span> ');

    return (
        <span 
            dangerouslySetInnerHTML={{ __html: formattedHTML }} 
            className="leading-relaxed"
        />
    );
};
