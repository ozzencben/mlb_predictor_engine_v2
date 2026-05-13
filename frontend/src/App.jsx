import { usePredictions } from './hooks/usePredictions'
import MatchupCard from './components/MatchupCard'

function App() {
  const { data, loading, error } = usePredictions()

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
    </div>
  )

  if (error) return <div className="p-10 text-red-500 text-center">❌ Connection Error: {error}</div>

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8">
      {/* Header */}
      <header className="mb-10 flex flex-col md:flex-row justify-between items-end border-b border-gray-800 pb-6">
        <div>
          <h1 className="text-4xl font-black text-white italic tracking-tighter">TYLER MLB <span className="text-blue-500">PREDICTOR</span></h1>
          <p className="text-gray-500 text-sm font-bold">Data-Driven Insights for {data.data.date}</p>
        </div>
        <div className="mt-4 md:mt-0 text-right">
          <span className="text-[10px] text-gray-500 font-bold uppercase">System Status</span>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-xs font-bold text-green-500 uppercase">Live & Ready</span>
          </div>
        </div>
      </header>

      {/* Grid: Matchup Cards */}
      <div className="grid grid-cols-1 gap-4">
        {data.data.predictions.map((game, index) => (
          <MatchupCard key={index} prediction={game} />
        ))}
      </div>
    </div>
  )
}

export default App