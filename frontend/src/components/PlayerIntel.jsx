import React, { useState } from 'react';
import { usePlayerIntel } from '../hooks/usePlayer';
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

const PlayerIntel = ({ playerId }) => {
    const { data: intel, isLoading } = usePlayerIntel(playerId);
    const [isOpen, setIsOpen] = useState(false);

    if (isLoading || !intel || !intel.facts || intel.facts.length === 0) return null;

    return (
        <div className="mt-4 border border-court-border rounded-lg overflow-hidden bg-court-bg/50">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between px-4 py-3 bg-court-surface/30 hover:bg-court-surface/60 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <Sparkles size={16} className="text-court-orange" />
                    <span className="font-display tracking-widest text-sm text-court-text">PLAYER INTEL</span>
                </div>
                {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {isOpen && (
                <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 animate-in fade-in slide-in-from-top-1 duration-200">
                    {intel.facts.map((fact, idx) => (
                        <div key={idx} className="border border-court-border rounded px-3 py-2 text-xs flex items-center bg-court-bg">
                            <span className="text-court-subtext font-mono uppercase tracking-widest mr-2">{fact.label}</span>
                            <span className="text-court-text font-semibold truncate" title={fact.value}>{fact.value}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default PlayerIntel;
