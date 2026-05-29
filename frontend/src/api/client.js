import axios from 'axios';

// Detect if the browser is running on localhost
const isLocalhost = typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1');

// Auto-switch baseURL: local offline dev queries local backend, production queries Render production API.
const baseURL = isLocalhost
    ? "http://localhost:8000/api/v1"
    : "https://mlb-predictor-engine-v2.onrender.com/api/v1";

// Tüm istekler için temel ayarlar
const apiClient = axios.create({
    baseURL,
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