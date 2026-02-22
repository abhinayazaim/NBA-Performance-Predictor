import React, { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import clsx from 'clsx';

function AnimatedNumber({ target, decimals = 1, duration = 500 }) {
    const [value, setValue] = useState(0);
    useEffect(() => {
        const end = parseFloat(target) || 0;
        const steps = 30;
        const increment = end / steps;
        let current = 0;
        let step = 0;
        const timer = setInterval(() => {
            step++;
            current = step >= steps ? end : current + increment;
            setValue(current);
            if (step >= steps) clearInterval(timer);
        }, duration / steps);
        return () => clearInterval(timer);
    }, [target]);
    return <>{value.toFixed(decimals)}</>;
}

const STAT_META = {
    PTS: { label: 'Points', color: '#FF7A00', decimals: 1 },
    REB: { label: 'Rebounds', color: '#38BDF8', decimals: 1 },
    AST: { label: 'Assists', color: '#34D399', decimals: 1 },
    STL: { label: 'Steals', color: '#FBBF24', decimals: 1 },
    BLK: { label: 'Blocks', color: '#A78BFA', decimals: 1 },
    TOV: { label: 'Turnovers', color: '#F87171', decimals: 1, inverse: true },
    FG_PCT: { label: 'FG%', color: '#FF7A00', decimals: 1, pct: true },
    FT_PCT: { label: 'FT%', color: '#34D399', decimals: 1, pct: true },
    FG3M: { label: '3PM', color: '#FBBF24', decimals: 1 },
    FPTS: { label: 'Fan Pts', color: '#FF7A00', decimals: 1, featured: true },
};

function StatCard({ statKey, data, index }) {
    const [mounted, setMounted] = useState(false);
    useEffect(() => {
        const t = setTimeout(() => setMounted(true), index * 55);
        return () => clearTimeout(t);
    }, [index]);

    if (!data) return null;
    const meta = STAT_META[statKey] || { label: statKey, color: '#FF7A00', decimals: 1 };
    const { value = 0, ci = 0, higher_is_better = true, season_avg = 0 } = data;
    const delta = value - season_avg;
    const isPositive = delta > 0;
    const isGood = (meta.inverse || !higher_is_better) ? !isPositive : isPositive;
    const absDelta = Math.abs(delta);

    return (
        <div
            className="relative bg-court-surface border border-court-border rounded-xl p-4 overflow-hidden group
                       hover:-translate-y-0.5 hover:shadow-lg hover:border-opacity-80 cursor-default"
            style={{
                opacity: mounted ? 1 : 0,
                transform: mounted ? 'translateY(0)' : 'translateY(8px)',
                transition: `opacity 0.35s ease ${index * 0.055}s, transform 0.35s ease ${index * 0.055}s, box-shadow 0.2s, border-color 0.2s`,
            }}
        >
            {/* Color accent top bar */}
            <div
                className="absolute top-0 left-0 right-0 h-[2px] opacity-30 group-hover:opacity-100 transition-opacity duration-300"
                style={{ background: meta.color }}
            />

            {/* Label row */}
            <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-mono text-court-muted uppercase tracking-[0.18em]">
                    {meta.label}
                </span>
                {absDelta > 0.05 && (
                    <span className={clsx(
                        'flex items-center gap-0.5 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded-md',
                        isGood ? 'text-emerald-400 bg-emerald-400/10' : 'text-red-400 bg-red-400/10'
                    )}>
                        {isPositive ? <TrendingUp size={9} /> : <TrendingDown size={9} />}
                        {absDelta.toFixed(1)}
                    </span>
                )}
            </div>

            {/* Big value */}
            <div
                className="text-4xl font-display leading-none mb-3 transition-colors duration-300"
                style={{ color: meta.featured ? meta.color : '#CBD5E1' }}
            >
                {mounted
                    ? (<><AnimatedNumber target={value} decimals={meta.decimals} />{meta.pct ? '%' : ''}</>)
                    : (<>{(0).toFixed(meta.decimals)}{meta.pct ? '%' : ''}</>)
                }
            </div>

            {/* CI + avg footer */}
            <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono text-court-muted" title="±1σ confidence interval">
                    ±{ci.toFixed(1)}
                </span>
                <span className="text-[10px] font-mono text-court-muted">
                    avg {season_avg.toFixed(1)}{meta.pct ? '%' : ''}
                </span>
            </div>

            {/* Bottom progress bar showing delta magnitude */}
            <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-court-border/30">
                <div
                    className="h-full transition-all duration-700 ease-out"
                    style={{
                        width: mounted ? `${Math.min(100, (absDelta / Math.max(season_avg, 1)) * 200)}%` : '0%',
                        background: isGood ? '#34D399' : '#F87171',
                        opacity: 0.6,
                        transitionDelay: `${index * 0.055 + 0.3}s`,
                    }}
                />
            </div>
        </div>
    );
}

export default function StatCards({ predictions }) {
    if (!predictions || Object.keys(predictions).length === 0) return null;
    const row1 = ['PTS', 'REB', 'AST', 'STL', 'BLK'];
    const row2 = ['TOV', 'FG_PCT', 'FT_PCT', 'FG3M', 'FPTS'];
    return (
        <div className="space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                {row1.map((s, i) => <StatCard key={s} statKey={s} data={predictions[s]} index={i} />)}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                {row2.map((s, i) => <StatCard key={s} statKey={s} data={predictions[s]} index={i + 5} />)}
            </div>
        </div>
    );
}