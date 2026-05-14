import { usePredictions } from './hooks/usePredictions'
import MatchupCard from './components/MatchupCard'
import MatchupSkeleton from './components/MatchupSkeleton' // Yeni ekledik
import Footer from './components/Footer'

function App() {
  const { data, loading, error } = usePredictions()

  // Hata durumunda hala tam ekran uyarı vermek mantıklı
  if (error) return <div className="p-10 text-red-500 text-center font-black">❌ Connection Error: {error}</div>

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8">
      {/* ================= HEADER ================= */}
      <header className="mb-10 flex flex-col md:flex-row justify-between items-end border-b border-gray-800 pb-6">
        <div>
          <h1 className="text-4xl font-black text-white italic tracking-tighter">
            TYLER MLB <span className="text-blue-500">PREDICTOR</span>
          </h1>
          <p className="text-gray-500 text-sm font-bold tracking-tight">
            {/* Loading sırasında tarih henüz gelmediği için korumalı yazdık */}
            Data-Driven Insights for {loading ? 'Loading...' : data?.data?.date}
          </p>
        </div>

        <div className="mt-4 md:mt-0 text-right">
          {/* Son Güncelleme Bilgisi - Sadece veri varsa gösterilir */}
          {!loading && data?.data?.last_updated && (
            <div className="mb-1">
              <span className="text-[9px] text-gray-600 font-black uppercase tracking-[0.2em]">
                Last Update: <span className="text-gray-400">{data.data.last_updated}</span>
              </span>
            </div>
          )}

          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">
            System Status
          </span>
          <div className="flex items-center justify-end gap-2 mt-0.5">
            <div className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </div>
            <span className="text-xs font-bold text-green-500 uppercase tracking-tighter">
              {loading ? 'Syncing...' : 'Live & Ready'}
            </span>
          </div>
        </div>
      </header>

      {/* ================= KARTLARIN OLDUĞU BÖLÜM ================= */}
      <div className="grid grid-cols-1 gap-4">
        {loading ? (
          // Yükleme sırasında 3 adet Skeleton gösteriyoruz
          <>
            <MatchupSkeleton />
            <MatchupSkeleton />
            <MatchupSkeleton />
          </>
        ) : (
          // Veri geldiğinde gerçek kartlar
          data?.data?.predictions.map((game, index) => (
            <MatchupCard key={index} prediction={game} />
          ))
        )}
      </div>

      <Footer />
    </div>
  )
}

export default App