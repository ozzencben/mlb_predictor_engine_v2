import axios from 'axios';

// Tüm istekler için temel ayarlar
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1",
  timeout: 10000, // 10 saniye sonra yanıt gelmezse iptal et
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