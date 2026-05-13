import { useState, useEffect } from 'react';
import apiClient from '../api/client';

export const usePredictions = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchPredictions = async () => {
            try {
                setLoading(true);
                // Sadece endpoint ismini yazıyoruz, baseURL apiClient'tan geliyor
                const response = await apiClient.get('/predictions');
                setData(response.data);
                setError(null);
            } catch (err) {
                setError(err.response?.data?.detail || err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchPredictions();
    }, []);

    return { data, loading, error };
};