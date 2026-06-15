import { useState, useEffect } from 'react';
import apiClient from '../api/client';

export const useTennisPredictions = (date = null) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isPreparing, setIsPreparing] = useState(false);

    useEffect(() => {
        let timer = null;
        let isMounted = true;

        const fetchTennisData = async (showLoading = true) => {
            if (showLoading) setLoading(true);
            try {
                const queryDate = date ? `?date=${date}` : '';
                
                // Fetch predictions and results in parallel
                const [predRes, resultsRes] = await Promise.all([
                    apiClient.get(`/tennis/predictions${queryDate}`),
                    apiClient.get(`/tennis/results${queryDate}`).catch(err => {
                        // Allow results to fail gracefully (e.g. 404 if no results exist yet for the day)
                        console.warn("Tennis results not available yet:", err.message);
                        return { data: { data: null } };
                    })
                ]);

                if (isMounted) {
                    setData({
                        predictions: predRes.data?.data || null,
                        last_updated: predRes.data?.last_updated || null,
                        results: resultsRes.data?.data || null,
                    });
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
                        // Retry polling in 10 seconds
                        timer = setTimeout(() => {
                            fetchTennisData(false);
                        }, 10000);
                    } else {
                        setError(errMsg);
                        setIsPreparing(false);
                        setLoading(false);
                    }
                }
            }
        };

        fetchTennisData();

        return () => {
            isMounted = false;
            if (timer) clearTimeout(timer);
        };
    }, [date]);

    return { data, loading, error, isPreparing };
};
