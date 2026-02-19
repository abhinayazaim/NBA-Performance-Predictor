import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea, AreaChart, Area, ReferenceLine, Label } from 'recharts';
import { TrendingUp } from 'lucide-react';
import clsx from 'clsx';

const TABS = [
    { id: 'PTS', label: 'Points' },
    { id: 'REB', label: 'Rebounds' },
    { id: 'AST', label: 'Assists' },
    { id: 'STL', label: 'Steals' },
    { id: 'BLK', label: 'Blocks' },
    { id: 'FPTS', label: 'Fantasy' },
];

const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-court-surface border border-court-border rounded px-3 py-2 shadow-lg">
                <p className="text-court-subtext text-xs font-mono mb-1">{label}</p>
                {payload.map((entry, i) => (
                    <p key={i} className="text-court-orange font-mono text-sm font-semibold">
                        {entry.name}: <span className="text-white">{typeof entry.value === 'number' ? entry.value.toFixed(1) : entry.value}</span>
                    </p>
                ))}
            </div>
        )
    }
    return null
}

export default function TrendCharts({ history, predictions }) {
    const [activeTab, setActiveTab] = useState('PTS');

    if (!history || !predictions) return null;

    // Prepare data: History + Prediction
    const data = history?.slice().reverse()?.map(game => ({
        ...game,
        value: game[activeTab],
        GAME_DATE: new Date(game.GAME_DATE).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    })) || [];

    const predictionValue = predictions?.[activeTab]?.value;
    const predictionCi = predictions?.[activeTab]?.ci;

    return (
        <div className="bg-court-surface border border-court-border rounded-lg p-6">
            <div className="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
                <h3 className="text-court-orange text-xs font-bold uppercase tracking-widest flex items-center gap-2">
                    <TrendingUp size={14} /> Trend Analysis
                </h3>

                <div className="flex bg-court-bg/50 p-1 rounded-lg border border-court-border overflow-x-auto max-w-full">
                    {TABS.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={clsx(
                                "px-3 py-1 text-xs font-mono rounded transition-all whitespace-nowrap",
                                activeTab === tab.id
                                    ? "bg-court-orange text-white shadow-lg"
                                    : "text-court-subtext hover:text-court-text hover:bg-court-border/50"
                            )}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data}>
                        <defs>
                            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#FF7A00" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#FF7A00" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <XAxis
                            dataKey="GAME_DATE"
                            stroke="#64748B"
                            tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'monospace' }}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis
                            stroke="#64748B"
                            tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'monospace' }}
                            tickLine={false}
                            axisLine={false}
                            domain={['auto', 'auto']}
                        />
                        <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#0F1520', borderColor: '#1A2235', color: '#E2E8F0' }}
                            cursor={{ stroke: '#FF7A00', strokeWidth: 1, strokeDasharray: '4 4' }}
                            formatter={(val) => [val, activeTab]}
                        />
                        <Area
                            type="monotone"
                            dataKey="value"
                            stroke="#FF7A00"
                            strokeWidth={2}
                            fillOpacity={1}
                            fill="url(#colorValue)"
                        />
                        {/* Prediction Reference Line */}
                        {predictionValue && (
                            <ReferenceLine y={predictionValue} stroke="#38BDF8" strokeDasharray="3 3">
                                <Label value="PRED" position="insideTopRight" fill="#38BDF8" fontSize={10} />
                            </ReferenceLine>
                        )}
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {predictionValue && (
                <div className="flex justify-center mt-4 gap-6 text-xs font-mono text-court-subtext">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-0.5 bg-court-orange"></div>
                        <span>Trend</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-0.5 bg-[#38BDF8] border-dashed border-t border-b-0"></div>
                        <span>Forecast: {predictionValue.toFixed(1)} ± {predictionCi?.toFixed(1)}</span>
                    </div>
                </div>
            )}
        </div>
    );
}
