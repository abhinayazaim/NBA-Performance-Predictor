import React, { useState } from 'react';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, ReferenceLine, ReferenceArea
} from 'recharts';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import clsx from 'clsx';

const TABS = [
    { id: 'PTS', label: 'PTS', color: '#FF7A00' },
    { id: 'REB', label: 'REB', color: '#38BDF8' },
    { id: 'AST', label: 'AST', color: '#34D399' },
    { id: 'STL', label: 'STL', color: '#FBBF24' },
    { id: 'BLK', label: 'BLK', color: '#A78BFA' },
    { id: 'FPTS', label: 'FPTS', color: '#FF7A00' },
];

const CustomTooltip = ({ active, payload, label, color }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
        <div className="bg-court-bg border border-court-border rounded-lg px-3 py-2.5 shadow-2xl min-w-[100px]">
            <p className="text-[10px] font-mono text-court-muted tracking-widest mb-1.5 uppercase">{label}</p>
            <p className="font-display text-xl" style={{ color }}>
                {typeof payload[0]?.value === 'number' ? payload[0].value.toFixed(1) : '--'}
            </p>
            {d?.wl && (
                <p className={`text-[10px] font-mono mt-1 ${d.wl === 'W' ? 'text-emerald-400' : 'text-red-400'}`}>
                    {d.wl === 'W' ? '● Win' : '○ Loss'}
                </p>
            )}
        </div>
    );
};

export default function TrendCharts({ history, predictions }) {
    const [activeTab, setActiveTab] = useState('PTS');
    if (!history?.length || !predictions) return null;

    const tab = TABS.find(t => t.id === activeTab) || TABS[0];
    const predVal = predictions?.[activeTab]?.value;
    const predCi = predictions?.[activeTab]?.ci || 0;
    const seasonAvg = predictions?.[activeTab]?.season_avg;

    const chartData = [...history].slice(0, 20).reverse().map((g, i) => ({
        date: g.GAME_DATE ? String(g.GAME_DATE).slice(5) : `G${i + 1}`,
        value: parseFloat(g[activeTab]) || 0,
        wl: g.WL,
    }));

    const last5Avg = chartData.slice(-5).reduce((s, d) => s + d.value, 0) / Math.max(1, Math.min(5, chartData.length));
    const trendDir = !predVal ? 'flat' : predVal > last5Avg + 0.5 ? 'up' : predVal < last5Avg - 0.5 ? 'down' : 'flat';

    return (
        <div className="bg-court-surface border border-court-border rounded-xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-court-border">
                <div className="flex items-center gap-3">
                    <TrendingUp size={13} className="text-court-orange" />
                    <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-court-subtext">Trend Analysis</span>
                    {predVal != null && (
                        <div className="flex items-center gap-2 ml-1">
                            <span
                                className="text-xs font-mono font-bold px-2 py-0.5 rounded"
                                style={{ color: tab.color, background: `${tab.color}15` }}
                            >
                                PRED {predVal.toFixed(1)}
                            </span>
                            <span className={clsx(
                                'text-[10px] font-mono flex items-center gap-0.5',
                                trendDir === 'up' ? 'text-emerald-400' : trendDir === 'down' ? 'text-red-400' : 'text-court-muted'
                            )}>
                                {trendDir === 'up' ? <TrendingUp size={9} /> : trendDir === 'down' ? <TrendingDown size={9} /> : <Minus size={9} />}
                                {trendDir === 'up' ? 'Hot' : trendDir === 'down' ? 'Cold' : 'Steady'}
                            </span>
                        </div>
                    )}
                </div>

                {/* Tab pills */}
                <div className="flex gap-1 bg-court-bg/60 p-1 rounded-lg border border-court-border">
                    {TABS.map(t => (
                        <button
                            key={t.id}
                            onClick={() => setActiveTab(t.id)}
                            className="px-2.5 py-1 text-[10px] font-mono font-bold rounded transition-all duration-200 tracking-wider"
                            style={activeTab === t.id
                                ? { background: t.color, color: '#080C14' }
                                : { color: '#4A5568' }
                            }
                        >
                            {t.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Chart */}
            <div className="px-2 pt-4 pb-1" style={{ height: 270 }}>
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 10, right: 20, left: -12, bottom: 0 }}>
                        <defs>
                            <linearGradient id={`grad-${activeTab}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={tab.color} stopOpacity={0.2} />
                                <stop offset="100%" stopColor={tab.color} stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1A2235" vertical={false} />
                        <XAxis
                            dataKey="date"
                            tick={{ fill: '#374151', fontSize: 9, fontFamily: 'monospace' }}
                            tickLine={false} axisLine={false}
                        />
                        <YAxis
                            tick={{ fill: '#374151', fontSize: 9, fontFamily: 'monospace' }}
                            tickLine={false} axisLine={false}
                            domain={['auto', 'auto']}
                        />
                        <Tooltip content={<CustomTooltip color={tab.color} />}
                            cursor={{ stroke: tab.color, strokeWidth: 1, strokeDasharray: '4 4', opacity: 0.4 }} />

                        {/* Season average */}
                        {seasonAvg != null && (
                            <ReferenceLine y={seasonAvg} stroke="#374151" strokeDasharray="4 3" strokeWidth={1}
                                label={{ value: `avg ${seasonAvg.toFixed(1)}`, fill: '#4B5563', fontSize: 9, position: 'insideTopLeft', fontFamily: 'monospace' }}
                            />
                        )}

                        {/* Confidence band */}
                        {predVal != null && predCi > 0 && (
                            <ReferenceArea y1={predVal - predCi} y2={predVal + predCi} fill={tab.color} fillOpacity={0.06} />
                        )}

                        {/* Prediction line */}
                        {predVal != null && (
                            <ReferenceLine y={predVal} stroke={tab.color} strokeDasharray="6 3" strokeWidth={1.5} opacity={0.75}
                                label={{ value: `← ${predVal.toFixed(1)}`, fill: tab.color, fontSize: 9, position: 'right', fontFamily: 'monospace' }}
                            />
                        )}

                        <Area
                            type="monotone" dataKey="value"
                            stroke={tab.color} strokeWidth={2}
                            fill={`url(#grad-${activeTab})`}
                            dot={(props) => {
                                const { cx, cy, payload, index } = props;
                                return (
                                    <circle key={`dot-${index}`} cx={cx} cy={cy} r={3}
                                        fill={payload.wl === 'W' ? tab.color : '#1F2937'}
                                        stroke={tab.color} strokeWidth={1.5}
                                    />
                                );
                            }}
                            activeDot={{ r: 5, fill: tab.color, stroke: '#080C14', strokeWidth: 2 }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div className="flex items-center justify-between px-5 py-2.5 border-t border-court-border/40 bg-court-bg/20">
                <div className="flex gap-4">
                    {[
                        { swatch: <div className="w-5 h-[2px]" style={{ background: tab.color }} />, label: 'Actual' },
                        { swatch: <div className="w-5 h-[1px] border-t border-dashed" style={{ borderColor: tab.color }} />, label: `Forecast ± ${predCi.toFixed(1)}` },
                        { swatch: <div className="w-2 h-2 rounded-full" style={{ background: tab.color }} />, label: 'Win' },
                        { swatch: <div className="w-2 h-2 rounded-full border" style={{ background: '#1F2937', borderColor: tab.color }} />, label: 'Loss' },
                    ].map((item, i) => (
                        <div key={i} className="flex items-center gap-1.5">
                            {item.swatch}
                            <span className="text-[9px] font-mono text-court-muted">{item.label}</span>
                        </div>
                    ))}
                </div>
                <span className="text-[9px] font-mono text-court-muted">Last 20 games</span>
            </div>
        </div>
    );
}