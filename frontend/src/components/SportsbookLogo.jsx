import React, { useState } from 'react';

const SportsbookLogo = ({ bookmaker, size = 'sm' }) => {
    const [imgError, setImgError] = useState(false);
    if (!bookmaker) return null;

    const normalized = bookmaker.toLowerCase().replace(/\s+/g, '');
    const bookmakerConfig = {
        'draftkings': { domain: 'draftkings.com', name: 'DK', color: '#51B046', textColor: '#ffffff' },
        'fanduel': { domain: 'fanduel.com', name: 'FD', color: '#1480f0', textColor: '#ffffff' },
        'caesars': { domain: 'caesars.com', name: 'CZ', color: '#c99a2e', textColor: '#ffffff' },
        'betmgm': { domain: 'betmgm.com', name: 'MGM', color: '#cc9933', textColor: '#000000' },
        'fanatics': { domain: 'fanatics.com', name: 'FN', color: '#d22630', textColor: '#ffffff' },
        'pointsbet': { domain: 'pointsbet.com', name: 'PB', color: '#e21e26', textColor: '#ffffff' },
        'betrivers': { domain: 'betrivers.com', name: 'BR', color: '#092140', textColor: '#ffffff' },
        'bovada': { domain: 'bovada.lv', name: 'BV', color: '#cc0000', textColor: '#ffffff' },
        'mybookie': { domain: 'mybookie.ag', name: 'MY', color: '#ffb300', textColor: '#000000' },
        'betus': { domain: 'betus.com.pa', name: 'US', color: '#002855', textColor: '#ffffff' },
    };

    let config = null;
    for (const key in bookmakerConfig) {
        if (normalized.includes(key)) {
            config = bookmakerConfig[key];
            break;
        }
    }

    if (!config) {
        config = {
            domain: `${normalized}.com`,
            name: bookmaker.substring(0, 3).toUpperCase(),
            color: '#00f2fe',
            textColor: '#000000'
        };
    }

    const faviconUrl = `https://www.google.com/s2/favicons?domain=${config.domain}&sz=32`;
    const sizeClasses = size === 'xs' ? 'w-4 h-4 text-[8px]' : size === 'sm' ? 'w-5 h-5 text-[10px]' : 'w-6 h-6 text-xs';

    if (imgError) {
        return (
            <span 
                className={`inline-flex items-center justify-center rounded font-extrabold uppercase px-1 border border-slate-700/50 tracking-tighter ${sizeClasses}`}
                style={{ 
                    backgroundColor: config.color, 
                    color: config.textColor,
                    boxShadow: `0 0 4px ${config.color}80`
                }}
                title={bookmaker}
            >
                {config.name}
            </span>
        );
    }

    return (
        <span className="inline-flex items-center justify-center">
            <img 
                src={faviconUrl} 
                alt={bookmaker}
                className={`inline-block rounded bg-slate-800 p-[2px] object-contain border border-slate-700/50 ${size === 'xs' ? 'w-4 h-4' : size === 'sm' ? 'w-5 h-5' : 'w-6 h-6'}`}
                onError={() => setImgError(true)}
                title={bookmaker}
                loading="lazy"
                width={size === 'xs' ? 16 : size === 'sm' ? 20 : 24}
                height={size === 'xs' ? 16 : size === 'sm' ? 20 : 24}
            />
        </span>
    );
};

export default SportsbookLogo;
