import React from 'react';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import clsx from 'clsx';

const StatCard = ({ label, data }) => {
    if (!data) return null;
    const { value, ci, higher_is_better, season_avg } = data;

    const delta = (value || 0) - (season_avg || 0);
    const isPositive = delta > 0;

    // Logic: 
    // If higher_is_better: Positive delta = Good (Green), Negative = Bad (Red)
    // If NOT higher_is_better (TOV): Positive delta = Bad (Red), Negative = Good (Green)
    const isGood = higher_is_better ? isPositive : !isPositive;

    const colorClass = isGood ? 'text-court-green' : 'text-court-red';
    const Icon = isPositive ? TrendingUp : TrendingDown;

    // Formatting
    let displayValue = value || 0;
    if (label.includes('PCT')) displayValue = `${(value || 0).toFixed(1)}%`;
    else if (['PTS', 'REB', 'AST', 'FPTS'].includes(label)) displayValue = (value || 0).toFixed(1);
    else displayValue = (value || 0).toFixed(1);

    return (
        <div className="bg-court-surface border border-court-border rounded p-4 relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-full h-[2px] bg-court-orange opacity-0 group-hover:opacity-100 transition-opacity" />

            <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-mono text-court-subtext uppercase tracking-widest">{label}</span>
                <span className={clsx("flex items-center gap-1 text-xs font-mono", colorClass)}>
                    <Icon size={12} />
                    {Math.abs(delta).toFixed(1)}
                </span>
            </div>

            <div className="text-4xl font-display text-court-text mb-2">
                {displayValue}
            </div>

            <div
                className="text-xs text-court-muted font-mono flex items-center gap-1 cursor-help"
                title="Confidence Interval — 68% of outcomes expected within this range"
            >
                <Activity size={10} />
                ± {(ci || 0).toFixed(1)}
            </div>
        </div>
    );
};

export default function StatCards({ predictions }) {
    if (!predictions) return null;

    const row1 = ['PTS', 'REB', 'AST', 'STL', 'BLK'];
    const row2 = ['TOV', 'FG_PCT', 'FT_PCT', 'FG3M', 'FPTS'];

    return (
        <div className="grid gap-4 mb-6">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {row1.map(stat => <StatCard key={stat} label={stat} data={predictions?.[stat]} />)}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {row2.map(stat => <StatCard key={stat} label={stat} data={predictions?.[stat]} />)}
            </div>
        </div>
    );
}
