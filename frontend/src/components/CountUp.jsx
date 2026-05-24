import React, { useState, useEffect } from 'react';

const CountUp = ({ end, duration = 800, decimals = 1, suffix = '' }) => {
    const [value, setValue] = useState(0);

    useEffect(() => {
        const endValue = parseFloat(end);
        if (isNaN(endValue)) {
            setValue(end);
            return;
        }

        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            
            // Cubic easeOut for smooth slowdown
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            
            setValue(easeProgress * endValue);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }, [end, duration]);

    if (isNaN(parseFloat(end))) {
        return <span>{end}</span>;
    }

    return <span>{value.toFixed(decimals)}{suffix}</span>;
};

export default CountUp;
