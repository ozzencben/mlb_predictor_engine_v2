// Amerikan Oran Formatlayıcı (Decimal'den Amerikan'a)
export const formatAmericanOdds = (decimal) => {
    if (!decimal || decimal <= 1) return "N/A";
    if (decimal >= 2.0) {
        return "+" + Math.round((decimal - 1) * 100);
    } else {
        return Math.round(-100 / (decimal - 1));
    }
};

// Takım Logoları İçin CDN (MLB resmi logoları)
export const getTeamLogo = (teamName) => {
    // Takım isimlerini MLB logolarıyla eşleştirecek bir nesne
    // Not: Backend'den gelen isimlere göre burayı genişletebiliriz.
    const logos = {
        "NY Yankees": "https://www.mlbstatic.com/team-logos/147.svg",
        "Baltimore": "https://www.mlbstatic.com/team-logos/110.svg",
        "LA Angels": "https://www.mlbstatic.com/team-logos/108.svg",
        "Cleveland": "https://www.mlbstatic.com/team-logos/114.svg",
        "Washington": "https://www.mlbstatic.com/team-logos/120.svg",
        "Cincinnati": "https://www.mlbstatic.com/team-logos/113.svg",
        "Colorado": "https://www.mlbstatic.com/team-logos/115.svg",
        "Pittsburgh": "https://www.mlbstatic.com/team-logos/134.svg",
        "Philadelphia": "https://www.mlbstatic.com/team-logos/143.svg",
        "Boston": "https://www.mlbstatic.com/team-logos/111.svg",
        "Tampa Bay": "https://www.mlbstatic.com/team-logos/139.svg",
        "Toronto": "https://www.mlbstatic.com/team-logos/141.svg",
        "Detroit": "https://www.mlbstatic.com/team-logos/116.svg",
        "NY Mets": "https://www.mlbstatic.com/team-logos/121.svg",
        "Chi Cubs": "https://www.mlbstatic.com/team-logos/112.svg",
        "Atlanta": "https://www.mlbstatic.com/team-logos/144.svg",
        "Kansas City": "https://www.mlbstatic.com/team-logos/118.svg",
        "Chi White Sox": "https://www.mlbstatic.com/team-logos/145.svg",
        "Miami": "https://www.mlbstatic.com/team-logos/146.svg",
        "Minnesota": "https://www.mlbstatic.com/team-logos/142.svg",
        "San Diego": "https://www.mlbstatic.com/team-logos/135.svg",
        "Milwaukee": "https://www.mlbstatic.com/team-logos/158.svg",
        "Arizona": "https://www.mlbstatic.com/team-logos/109.svg",
        "Texas": "https://www.mlbstatic.com/team-logos/140.svg",
        "Seattle": "https://www.mlbstatic.com/team-logos/136.svg",
        "Houston": "https://www.mlbstatic.com/team-logos/117.svg",
        "St Louis": "https://www.mlbstatic.com/team-logos/138.svg",
        "Athletics": "https://www.mlbstatic.com/team-logos/133.svg",
        "SF Giants": "https://www.mlbstatic.com/team-logos/137.svg",
        "LA Dodgers": "https://www.mlbstatic.com/team-logos/119.svg"
    };
    return logos[teamName] || "https://www.mlbstatic.com/team-logos/league/1.svg";
};