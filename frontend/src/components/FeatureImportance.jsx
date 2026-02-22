import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Brain } from 'lucide-react';

function cleanName(name) {
    return name
        .replace('ROLLING_', '')
        .replace('TREND_', 'TREND ')
        .replace(/_(\d+)$/, ' ($1g)')
        .replace('STD_', 'VOL ')
        .replace('OPP_DEF_RANK', 'OPP DEF RANK')
        .replace('OPP_DEF_NORM', 'OPP DEF')
        .replace('WIN_PCT_LAST', 'WIN% L')
        .replace('IS_HOME', 'HOME GAME')
        .replace('REST_DAYS', 'REST DAYS')
        .replace('REST_B2B', 'BACK-TO-BACK')
        .replace('REST_NORMAL', 'NORMAL REST')
        .replace('MIN_TREND', 'MIN TREND')
        .replace('GAME_NUM', 'GAME #')
        .toLowerCase()
        .replace(/\b\w/g, c => c.toUpperCase());
}

const COLORS = ['#FF7A00', '#FF9A33', '#FFB466', '#FFC880', '#FFD699'];

export default function FeatureImportance({ features }) {
    const [isOpen, setIsOpen] = useState(false);
    if (!features?.length) return null;

    const top = features.slice(0, 8);
    const maxImp = top[0]?.importance || 1;

    return (
        <div className="bg-court-surface border border-court-border rounded-xl overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-court-bg/30 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <Brain size={13} className="text-court-orange" />
                    <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-court-subtext">
                        Why this prediction?
                    </span>
                </div>
                {isOpen
                    ? <ChevronUp size={14} className="text-court-muted" />
                    : <ChevronDown size={14} className="text-court-muted" />
                }
            </button>

            {isOpen && (
                <div className="px-5 pb-4 pt-1 space-y-2.5 border-t border-court-border/40">
                    {top.map((feat, i) => (
                        <div key={i} className="flex items-center gap-3">
                            <div className="w-28 text-[10px] font-mono text-court-muted truncate shrink-0" title={feat.name}>
                                {cleanName(feat.name)}
                            </div>
                            <div className="flex-1 h-1.5 bg-court-bg rounded-full overflow-hidden">
                                <div
                                    className="h-full rounded-full transition-all duration-700"
                                    style={{
                                        width: `${(feat.importance / maxImp) * 100}%`,
                                        background: COLORS[Math.min(i, COLORS.length - 1)],
                                        opacity: 1 - (i * 0.08),
                                        transitionDelay: `${i * 0.05}s`,
                                    }}
                                />
                            </div>
                            <div className="w-10 text-right text-[10px] font-mono text-court-subtext shrink-0">
                                {(feat.importance * 100).toFixed(1)}%
                            </div>
                        </div>
                    ))}
                    <p className="text-[9px] font-mono text-court-muted pt-1">
                        Based on PTS model feature importances
                    </p>
                </div>
            )}
        </div>
    );
}