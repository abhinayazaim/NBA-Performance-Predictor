import React, { useState } from 'react';
import { ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';

export default function FeatureImportance({ features }) {
    const [isOpen, setIsOpen] = useState(false);

    if (!features || features.length === 0) return null;

    const maxImp = Math.max(...features.map(f => f.importance));

    return (
        <div className="bg-court-bg border border-court-border rounded-lg p-4">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex justify-between items-center text-court-subtext hover:text-court-orange transition-colors"
            >
                <span className="text-xs font-bold uppercase tracking-widest flex items-center gap-2">
                    <AlertCircle size={14} /> Why this prediction?
                </span>
                {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {isOpen && (
                <div className="mt-4 space-y-3 pl-2">
                    {features.map((feat, idx) => (
                        <div key={idx} className="flex items-center gap-3">
                            <div className="w-32 text-xs font-mono text-court-subtext truncate" title={feat.name}>
                                {feat.name.replace('ROLLING_', '').replace('_10', '').replace('_5', '').replace('_20', '')}
                            </div>
                            <div className="flex-1 h-2 bg-court-surface rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-court-muted"
                                    style={{ width: `${(feat.importance / maxImp) * 100}%` }}
                                />
                            </div>
                            <div className="w-12 text-right text-xs font-mono text-court-text">
                                {(feat.importance * 100).toFixed(1)}%
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
