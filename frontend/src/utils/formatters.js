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
    if (!teamName) return "https://www.mlbstatic.com/team-logos/league/mlb.svg";
    const name = teamName.toLowerCase();
    
    if (name.includes('yankee')) return "https://www.mlbstatic.com/team-logos/147.svg";
    if (name.includes('red sox') || name.includes('boston')) return "https://www.mlbstatic.com/team-logos/111.svg";
    if (name.includes('blue jays') || name.includes('toronto')) return "https://www.mlbstatic.com/team-logos/141.svg";
    if (name.includes('oriole') || name.includes('baltimore')) return "https://www.mlbstatic.com/team-logos/110.svg";
    if (name.includes('rays') || name.includes('tampa')) return "https://www.mlbstatic.com/team-logos/139.svg";
    if (name.includes('twin') || name.includes('minnesota')) return "https://www.mlbstatic.com/team-logos/142.svg";
    if (name.includes('guardian') || name.includes('cleveland')) return "https://www.mlbstatic.com/team-logos/114.svg";
    if (name.includes('tiger') || name.includes('detroit')) return "https://www.mlbstatic.com/team-logos/116.svg";
    if (name.includes('white sox') || name.includes('chicago s') || name.includes('cws') || name.includes('chi white sox') || name.includes('chi. white sox') || name.includes('chi. s') || name.includes('chi s') || name.includes('sox') || name.includes('chicago white sox')) return "https://www.mlbstatic.com/team-logos/145.svg";
    if (name.includes('cubs') || name.includes('chicago c') || name.includes('chc') || name.includes('chi cubs') || name.includes('chi. cubs') || name.includes('chi. c') || name.includes('chi c') || name.includes('chicago cubs')) return "https://www.mlbstatic.com/team-logos/112.svg";
    if (name.includes('royal') || name.includes('kansas')) return "https://www.mlbstatic.com/team-logos/118.svg";
    if (name.includes('astros') || name.includes('houston')) return "https://www.mlbstatic.com/team-logos/117.svg";
    if (name.includes('mariner') || name.includes('seattle')) return "https://www.mlbstatic.com/team-logos/136.svg";
    if (name.includes('ranger') || name.includes('texas')) return "https://www.mlbstatic.com/team-logos/140.svg";
    if (name.includes('angel') || name.includes('laa') || name.includes('anaheim')) return "https://www.mlbstatic.com/team-logos/108.svg";
    if (name.includes('athletic') || name.includes('oakland') || name.includes('a\'s')) return "https://www.mlbstatic.com/team-logos/133.svg";
    if (name.includes('brave') || name.includes('atlanta')) return "https://www.mlbstatic.com/team-logos/144.svg";
    if (name.includes('mets') || name.includes('met') || name.includes('n.y. mets')) return "https://www.mlbstatic.com/team-logos/121.svg";
    if (name.includes('phillie') || name.includes('philadelphia')) return "https://www.mlbstatic.com/team-logos/143.svg";
    if (name.includes('marlin') || name.includes('miami')) return "https://www.mlbstatic.com/team-logos/146.svg";
    if (name.includes('national') || name.includes('washington') || name.includes('wsh')) return "https://www.mlbstatic.com/team-logos/120.svg";
    if (name.includes('brewer') || name.includes('milwaukee')) return "https://www.mlbstatic.com/team-logos/158.svg";
    if (name.includes('cardinal') || name.includes('st. l') || name.includes('st l')) return "https://www.mlbstatic.com/team-logos/138.svg";
    if (name.includes('pirate') || name.includes('pittsburgh')) return "https://www.mlbstatic.com/team-logos/134.svg";
    if (name.includes('reds') || name.includes('cincinnati')) return "https://www.mlbstatic.com/team-logos/113.svg";
    if (name.includes('dodger') || name.includes('los a')) return "https://www.mlbstatic.com/team-logos/119.svg";
    if (name.includes('giant') || name.includes('san f')) return "https://www.mlbstatic.com/team-logos/137.svg";
    if (name.includes('padre') || name.includes('san d')) return "https://www.mlbstatic.com/team-logos/135.svg";
    if (name.includes('diamondback') || name.includes('arizona')) return "https://www.mlbstatic.com/team-logos/109.svg";
    if (name.includes('rockie') || name.includes('colorado')) return "https://www.mlbstatic.com/team-logos/115.svg";

    return "https://www.mlbstatic.com/team-logos/league/mlb.svg";
};

// Takım Kısaltmaları
export const getTeamAbbr = (teamName) => {
    if (!teamName) return '';
    const name = teamName.toLowerCase();
    if (name.includes('yankee')) return 'NYY';
    if (name.includes('mets') || name.includes('met')) return 'NYM';
    if (name.includes('red sox') || name.includes('boston')) return 'BOS';
    if (name.includes('blue jays') || name.includes('toronto')) return 'TOR';
    if (name.includes('orioles') || name.includes('baltimore')) return 'BAL';
    if (name.includes('tampa') || name.includes('rays')) return 'TB';
    if (name.includes('twins') || name.includes('minnesota')) return 'MIN';
    if (name.includes('guardians') || name.includes('cleveland')) return 'CLE';
    if (name.includes('tigers') || name.includes('detroit')) return 'DET';
    if (name.includes('white sox') || name.includes('chicago s') || name.includes('cws') || name.includes('chi white sox') || name.includes('chi. white sox') || name.includes('chi. s') || name.includes('chi s') || name.includes('sox') || name.includes('chicago white sox')) return 'CWS';
    if (name.includes('cubs') || name.includes('chicago c') || name.includes('chc') || name.includes('chi cubs') || name.includes('chi. cubs') || name.includes('chi. c') || name.includes('chi c') || name.includes('chicago cubs')) return 'CHC';
    if (name.includes('royals') || name.includes('kansas')) return 'KC';
    if (name.includes('astros') || name.includes('houston')) return 'HOU';
    if (name.includes('mariners') || name.includes('seattle')) return 'SEA';
    if (name.includes('rangers') || name.includes('texas')) return 'TEX';
    if (name.includes('angels') || name.includes('laa')) return 'LAA';
    if (name.includes('athletics') || name.includes('oakland') || name.includes('a\'s')) return 'OAK';
    if (name.includes('braves') || name.includes('atlanta')) return 'ATL';
    if (name.includes('phillies') || name.includes('philadelphia')) return 'PHI';
    if (name.includes('marlins') || name.includes('miami')) return 'MIA';
    if (name.includes('nationals') || name.includes('washington') || name.includes('wsh') || name.includes('was')) return 'WSH';
    if (name.includes('brewers') || name.includes('milwaukee')) return 'MIL';
    if (name.includes('cardinals') || name.includes('st. l') || name.includes('st l')) return 'STL';
    if (name.includes('pirates') || name.includes('pittsburgh')) return 'PIT';
    if (name.includes('reds') || name.includes('cincinnati')) return 'CIN';
    if (name.includes('dodgers') || name.includes('los a')) return 'LAD';
    if (name.includes('giants') || name.includes('san f')) return 'SF';
    if (name.includes('padres') || name.includes('san d')) return 'SD';
    if (name.includes('diamondbacks') || name.includes('arizona')) return 'ARI';
    if (name.includes('rockies') || name.includes('colorado')) return 'COL';
    return teamName.substring(0, 3).toUpperCase();
};