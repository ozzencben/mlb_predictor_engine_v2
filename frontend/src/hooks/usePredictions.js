import { useState, useEffect } from 'react';
import apiClient from '../api/client';

export const usePredictions = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isPreparing, setIsPreparing] = useState(false);

    useEffect(() => {
        let timer = null;
        let isMounted = true;

        const fetchPredictions = async (showLoading = true) => {
            if (showLoading) setLoading(true);
            try {
                const response = await apiClient.get('/predictions');
                if (isMounted) {
                    setData(response.data);
                    setError(null);
                    setIsPreparing(false);
                    setLoading(false);
                }
            } catch (err) {
                const errMsg = err.response?.data?.detail || err.message;
                if (isMounted) {
                    const isPrep = err.response?.status === 503 || (errMsg && (errMsg.includes('hazır değil') || errMsg.includes('prepared') || errMsg.includes('preparing')));
                    
                    if (isPrep) {
                        setError(errMsg);
                        setIsPreparing(true);
                        setLoading(false);
                        // Poll again in 10 seconds
                        timer = setTimeout(() => {
                            fetchPredictions(false);
                        }, 10000);
                    } else {
                        setError(errMsg);
                        setIsPreparing(false);
                        setLoading(false);
                    }
                }
            }
        };

        fetchPredictions();

        return () => {
            isMounted = false;
            if (timer) clearTimeout(timer);
        };
    }, []);

    return { data, loading, error, isPreparing };
};