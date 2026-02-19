import React from 'react';
import { PieChart } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList } from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-court-surface border border-court-border rounded px-3 py-2">
                <p className="text-court-subtext text-xs font-mono">{label}</p>
                <p className="text-court-orange font-mono text-sm font-semibold">
                    Value: <span className="text-white">{payload[0].value.toFixed(1)}</span>
                </p>
            </div>
        )
    }
    return null
}

export default function FantasyBreakdown({ predictions }) {
    if (!predictions) return null;

    // Calculate contributions
    const data = [
        { name: 'PTS', value: predictions?.PTS?.value || 0, color: '#F87171' },
        { name: 'REB', value: (predictions?.REB?.value || 0) * 1.2, color: '#60A5FA' },
        { name: 'AST', value: (predictions?.AST?.value || 0) * 1.5, color: '#34D399' },
        { name: 'STL', value: (predictions?.STL?.value || 0) * 3, color: '#FBBF24' },
        { name: 'BLK', value: (predictions?.BLK?.value || 0) * 3, color: '#818CF8' },
        { name: 'TOV', value: (predictions?.TOV?.value || 0) * -1, color: '#EF4444' },
    ];

    const totalFpts = predictions?.FPTS?.value || 0;

    return (
        <div className="bg-court-surface border border-court-border rounded-lg p-6">
            <h3 className="text-court-orange text-xs font-bold uppercase tracking-widest mb-6 flex items-center gap-2">
                <PieChart size={14} /> Fantasy Breakdown
            </h3>

            <div className="h-64 w-full relative">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} layout="vertical" margin={{ left: 20, right: 30 }}>
                        <XAxis type="number" hide />
                        <YAxis
                            dataKey="name"
                            type="category"
                            tick={{ fill: '#94A3B8', fontSize: 10, fontFamily: 'monospace' }}
                            tickLine={false}
                            axisLine={false}
                            width={30}
                        />
                        <Tooltip
                            cursor={{ fill: 'transparent' }}
                            content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                    return (
                                        <div className="bg-court-bg border border-court-border p-2 rounded shadow-lg">
                                            <p className="text-court-text text-xs font-mono mb-1">{payload[0].payload.name}</p>
                                            <p className="text-court-orange font-bold text-sm">
                                                {payload[0].value.toFixed(1)} <span className="text-court-muted text-[10px] font-normal">FPTS</span>
                                            </p>
                                        </div>
                                    );
                                }
                                return null;
                            }}
                        />
                        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={20}>
                            {data.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                            <LabelList dataKey="value" position="right" fill="#94A3B8" fontSize={10} formatter={(val) => val.toFixed(1)} />
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>

                <div className="absolute bottom-0 right-0 p-4 text-right">
                    <div className="text-court-subtext text-xs font-mono uppercase tracking-widest mb-1">Proj. FPTS</div>
                    <div className="text-3xl font-display text-court-text">{totalFpts.toFixed(1)}</div>
                </div>
            </div>
        </div>
    );
}
