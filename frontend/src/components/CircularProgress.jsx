import React, { useState, useEffect } from 'react';

const CircularProgress = ({ percentage, size = 52, strokeWidth = 4 }) => {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const [offset, setOffset] = useState(circumference);

    const numericPct = parseFloat(percentage);
    const validPct = isNaN(numericPct) ? 50 : Math.max(0, Math.min(100, numericPct));

    useEffect(() => {
        const progressOffset = circumference - (validPct / 100) * circumference;
        const timer = setTimeout(() => setOffset(progressOffset), 150);
        return () => clearTimeout(timer);
    }, [validPct, circumference]);

    // Neon color theme mapping
    let colorClass = 'text-cyan-400';
    let glowColor = 'rgba(6, 182, 212, 0.4)';
    if (validPct >= 70) {
        colorClass = 'text-emerald-400';
        glowColor = 'rgba(16, 185, 129, 0.45)';
    } else if (validPct >= 55) {
        colorClass = 'text-amber-400';
        glowColor = 'rgba(245, 158, 11, 0.45)';
    }

    return (
        <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
            <svg width={size} height={size} className="transform -rotate-90">
                {/* Background track circle */}
                <circle
                    className="text-slate-800/80"
                    strokeWidth={strokeWidth}
                    stroke="currentColor"
                    fill="transparent"
                    r={radius}
                    cx={size / 2}
                    cy={size / 2}
                />
                {/* Glowing neon animated progress circle */}
                <circle
                    className={`${colorClass} transition-all duration-1000 ease-out`}
                    strokeWidth={strokeWidth}
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                    style={{ filter: `drop-shadow(0 0 4px ${glowColor})` }}
                    r={radius}
                    cx={size / 2}
                    cy={size / 2}
                />
            </svg>
            {/* Centered Percentage Text */}
            <div className="absolute flex flex-col items-center justify-center leading-none">
                <span className="text-[10px] md:text-xs font-black text-white">{validPct.toFixed(0)}%</span>
            </div>
        </div>
    );
};

export default CircularProgress;
