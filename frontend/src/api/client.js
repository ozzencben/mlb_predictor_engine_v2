import axios from 'axios';

// Tüm istekler için temel ayarlar
const apiClient = axios.create({
  baseURL: "https://mlb-predictor-engine-v2.onrender.com/api/v1",  // "http://localhost:8000/api/v1"
  headers: {
    'Content-Type': 'application/json',
  },
});

// İleride hata yakalama (Error Logging) eklemek için interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Hatası Yakalandı:", error.message);
    return Promise.reject(error);
  }
);

export default apiClient;