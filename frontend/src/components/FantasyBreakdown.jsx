import React from 'react';
import { Zap } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList } from 'recharts';

const BREAKDOWN = [
    { key: 'PTS', label: 'Points', mult: 1, color: '#FF7A00' },
    { key: 'REB', label: 'Rebounds', mult: 1.25, color: '#38BDF8' },
    { key: 'AST', label: 'Assists', mult: 1.5, color: '#34D399' },
    { key: 'STL', label: 'Steals', mult: 2, color: '#FBBF24' },
    { key: 'BLK', label: 'Blocks', mult: 2, color: '#A78BFA' },
    { key: 'TOV', label: 'Turnovers', mult: -0.5, color: '#F87171' },
];

export default function FantasyBreakdown({ predictions }) {
    if (!predictions) return null;

    const data = BREAKDOWN.map(b => ({
        name: b.label,
        short: b.key,
        value: Math.round(((predictions?.[b.key]?.value || 0) * b.mult) * 10) / 10,
        color: b.color,
        mult: b.mult,
    })).filter(d => d.value !== 0);

    const totalFpts = predictions?.FPTS?.value || 0;

    return (
        <div className="bg-court-surface border border-court-border rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-court-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Zap size={13} className="text-court-orange" />
                    <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-court-subtext">Fantasy Breakdown</span>
                </div>
                <div className="text-right">
                    <div className="text-[9px] font-mono text-court-muted uppercase tracking-widest">Proj. Total</div>
                    <div className="text-xl font-display text-court-orange leading-none">{totalFpts.toFixed(1)}</div>
                </div>
            </div>

            <div className="p-4" style={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} layout="vertical" margin={{ left: 56, right: 40, top: 4, bottom: 4 }}>
                        <XAxis type="number" hide domain={['dataMin', 'dataMax']} />
                        <YAxis
                            dataKey="name"
                            type="category"
                            tick={{ fill: '#6B7280', fontSize: 10, fontFamily: 'monospace' }}
                            tickLine={false} axisLine={false}
                            width={52}
                        />
                        <Tooltip
                            cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                            content={({ active, payload }) => {
                                if (!active || !payload?.length) return null;
                                const d = payload[0].payload;
                                return (
                                    <div className="bg-court-bg border border-court-border rounded-lg px-3 py-2 shadow-xl">
                                        <p className="text-[10px] font-mono text-court-muted mb-1">{d.name} × {d.mult}</p>
                                        <p className="font-display text-lg" style={{ color: d.color }}>
                                            {d.value > 0 ? '+' : ''}{d.value.toFixed(1)} pts
                                        </p>
                                    </div>
                                );
                            }}
                        />
                        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={16}>
                            {data.map((entry, i) => (
                                <Cell key={i} fill={entry.color} opacity={0.85} />
                            ))}
                            <LabelList
                                dataKey="value"
                                position="right"
                                fill="#9CA3AF"
                                fontSize={10}
                                fontFamily="monospace"
                                formatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`}
                            />
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            <div className="px-5 pb-3 flex flex-wrap gap-x-4 gap-y-1">
                {BREAKDOWN.map(b => (
                    <div key={b.key} className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full" style={{ background: b.color }} />
                        <span className="text-[9px] font-mono text-court-muted">
                            {b.key} ×{b.mult}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}