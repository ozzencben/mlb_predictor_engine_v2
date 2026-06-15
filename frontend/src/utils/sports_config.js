export const SPORTS_CONFIG = {
  HOME: {
    id: 'home',
    name: 'Home',
    icon: '🏠',
    status: 'ACTIVE',
    models: []
  },
  MLB: {
    id: 'mlb',
    name: 'MLB',
    icon: '⚾',
    status: 'ACTIVE',
    models: ['Predictions', 'NRFI Model', 'Pitchers']
  },
  TENNIS: {
    id: 'tennis',
    name: 'Tennis',
    icon: '🎾',
    status: 'BETA', // İlk etapta BETA/MOCK olarak görünecek
    models: ['Match Projections']
  },
  NBA: {
    id: 'nba',
    name: 'NBA',
    icon: '🏀',
    status: 'COMING_SOON',
    models: []
  },
  SOCCER: {
    id: 'soccer',
    name: 'Soccer',
    icon: '⚽',
    status: 'COMING_SOON',
    models: []
  }
};
