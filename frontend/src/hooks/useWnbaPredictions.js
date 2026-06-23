import { useState, useEffect } from 'react';
import apiClient from '../api/client';

const isPreparingError = (err) => {
    const status = err.response?.status;
    const msg = (err.response?.data?.detail || err.message || '').toLowerCase();
    return (
        status === 503 ||
        msg.includes('hazır değil') ||
        msg.includes('hazir degil') ||
        msg.includes('henuz hazir') ||
        msg.includes('prepared') ||
        msg.includes('preparing')
    );
};

export const useWnbaPredictions = (date = null) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isPreparing, setIsPreparing] = useState(false);

    useEffect(() => {
        let timer = null;
        let isMounted = true;

        const fetchWnbaData = async (showLoading = true) => {
            if (showLoading) setLoading(true);
            try {
                const queryDate = date ? `?date=${date}` : '';

                const [predRes, resultsRes, injuriesRes, standingsRes] = await Promise.all([
                    apiClient.get(`/wnba/predictions${queryDate}`),
                    apiClient.get(`/wnba/results${queryDate}`).catch(() => ({ data: { data: null } })),
                    apiClient.get('/wnba/injuries').catch(() => ({ data: { data: null } })),
                    apiClient.get('/wnba/standings').catch(() => ({ data: { standings: [] } })),
                ]);

                if (isMounted) {
                    setData({
                        predictions: predRes.data?.data || null,
                        last_updated: predRes.data?.last_updated || null,
                        results: resultsRes.data?.data || null,
                        injuries: injuriesRes.data?.data || null,
                        standings: standingsRes.data?.standings || [],
                    });
                    setError(null);
                    setIsPreparing(false);
                    setLoading(false);
                }
            } catch (err) {
                const errMsg = err.response?.data?.detail || err.message;
                if (isMounted) {
                    if (isPreparingError(err)) {
                        setError(errMsg);
                        setIsPreparing(true);
                        setLoading(false);
                        timer = setTimeout(() => fetchWnbaData(false), 10000);
                    } else {
                        setError(errMsg);
                        setIsPreparing(false);
                        setLoading(false);
                    }
                }
            }
        };

        fetchWnbaData();

        return () => {
            isMounted = false;
            if (timer) clearTimeout(timer);
        };
    }, [date]);

    return { data, loading, error, isPreparing };
};
