// logo: ESPN CDN URL varsa kullan, yoksa icon emoji fallback
const ESPN = 'https://a.espncdn.com/i/teamlogos/leagues/500';

export const SPORTS_CONFIG = {
  HOME: {
    id: 'home',
    name: 'Home',
    icon: '🏠',
    logo: null,
    status: 'ACTIVE',
    models: []
  },
  MLB: {
    id: 'mlb',
    name: 'MLB',
    icon: '⚾',
    logo: `${ESPN}/mlb.png`,
    status: 'ACTIVE',
    models: ['Predictions', 'NRFI Model', 'Pitchers']
  },
  TENNIS: {
    id: 'tennis',
    name: 'Tennis',
    icon: '🎾',
    logo: null,
    status: 'ACTIVE',
    models: ['Match Projections']
  },
  NBA: {
    id: 'nba',
    name: 'NBA',
    icon: '🏀',
    logo: `${ESPN}/nba.png`,
    status: 'BETA',
    models: []
  },
  SOCCER: {
    id: 'soccer',
    name: 'Soccer',
    icon: '⚽',
    logo: null,
    status: 'COMING_SOON',
    models: []
  },
  UFC: {
    id: 'ufc',
    name: 'UFC',
    icon: '🥊',
    logo: `${ESPN}/ufc.png`,
    status: 'COMING_SOON',
    models: []
  },
  NFL: {
    id: 'nfl',
    name: 'NFL',
    icon: '🏈',
    logo: `${ESPN}/nfl.png`,
    status: 'COMING_SOON',
    models: []
  },
  WNBA: {
    id: 'wnba',
    name: 'WNBA',
    icon: '🏀',
    logo: `${ESPN}/wnba.png`,
    status: 'COMING_SOON',
    models: []
  },
  NHL: {
    id: 'nhl',
    name: 'NHL',
    icon: '🏒',
    logo: `${ESPN}/nhl.png`,
    status: 'COMING_SOON',
    models: []
  },
  CBB: {
    id: 'cbb',
    name: 'CBB',
    icon: '🏀',
    logo: null,
    status: 'COMING_SOON',
    models: []
  },
  CFB: {
    id: 'cfb',
    name: 'CFB',
    icon: '🏈',
    logo: null,
    status: 'COMING_SOON',
    models: []
  },
  PGA: {
    id: 'pga',
    name: 'PGA Tour',
    icon: '⛳',
    logo: null,
    status: 'COMING_SOON',
    models: []
  }
};

