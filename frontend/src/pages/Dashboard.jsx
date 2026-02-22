import React from 'react';
import { usePlayerContext } from '../context/PlayerContext';
import { usePlayerProfile, usePlayerPrediction } from '../hooks/usePlayer';
import PlayerHeader from '../components/PlayerHeader';
import StatCards from '../components/StatCards';
import TrendCharts from '../components/TrendCharts';
import SeasonLog from '../components/SeasonLog';
import FantasyBreakdown from '../components/FantasyBreakdown';
import FeatureImportance from '../components/FeatureImportance';
import { Loader2, Activity } from 'lucide-react';

const QUICK_PICKS = [
    { id: 2544, name: 'LeBron James' },
    { id: 201939, name: 'Stephen Curry' },
    { id: 203999, name: 'Nikola Jokic' },
    { id: 203507, name: 'Giannis' },
    { id: 1629029, name: 'Luka Doncic' },
    { id: 1628369, name: 'Jayson Tatum' },
    { id: 1641705, name: 'Victor Wembanyama' },
    { id: 203954, name: 'Joel Embiid' },
];

function EmptyState({ onSelect }) {
    return (
        <div className="flex flex-col items-center justify-center min-h-[65vh] gap-8 select-none">
            {/* Wordmark */}
            <div className="text-center">
                <div className="font-display text-[80px] leading-none tracking-[0.15em] text-court-border/30 mb-2">
                    COURT<br />VISION
                </div>
                <p className="font-mono text-[11px] text-court-muted uppercase tracking-[0.35em]">
                    AI-Powered NBA Predictions
                </p>
            </div>

            {/* Quick picks */}
            <div className="flex flex-col items-center gap-3">
                <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-court-border">
                    — Quick Pick —
                </p>
                <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                    {QUICK_PICKS.map(p => (
                        <button
                            key={p.id}
                            onClick={() => onSelect(p.id)}
                            className="flex items-center gap-2 border border-court-border hover:border-court-orange
                                       text-court-subtext hover:text-court-text bg-court-surface/50 hover:bg-court-surface
                                       font-mono text-xs px-3 py-1.5 rounded-lg transition-all duration-200 group"
                        >
                            <img
                                src={`https://cdn.nba.com/headshots/nba/latest/1040x760/${p.id}.png`}
                                alt=""
                                className="w-5 h-5 rounded-full object-cover object-top border border-court-border/50 bg-court-bg shrink-0"
                                onError={(e) => { e.target.style.display = 'none'; }}
                            />
                            {p.name}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex items-center gap-2 text-court-border/40">
                <Activity size={12} />
                <span className="font-mono text-[10px] tracking-widest">Search any active NBA player above</span>
            </div>
        </div>
    );
}

function SkeletonCard() {
    return <div className="bg-court-surface border border-court-border rounded-xl h-28 animate-pulse" />;
}

export default function Dashboard() {
    const { selectedPlayerId, setSelectedPlayerId } = usePlayerContext();

    const {
        data: profile,
        isLoading: loadingProfile,
        error: errorProfile,
    } = usePlayerProfile(selectedPlayerId);

    const {
        data: predictionData,
        isLoading: loadingPrediction,
        error: errorPrediction,
    } = usePlayerPrediction(selectedPlayerId);

    if (!selectedPlayerId) {
        return <EmptyState onSelect={setSelectedPlayerId} />;
    }

    if (loadingProfile && !profile) {
        return (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
                <Loader2 size={28} className="animate-spin text-court-orange" />
                <p className="font-mono text-[11px] uppercase tracking-widest text-court-muted animate-pulse">
                    Scouting Player Data...
                </p>
            </div>
        );
    }

    if (errorProfile) {
        return (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
                <p className="font-mono text-sm text-red-400">Failed to load player profile</p>
                <button
                    onClick={() => setSelectedPlayerId(null)}
                    className="font-mono text-xs text-court-muted underline hover:text-court-subtext"
                >
                    Clear selection
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-5" style={{ animation: 'fadeIn 0.4s ease-out forwards' }}>
            <PlayerHeader profile={profile} />

            {/* Predictions section */}
            {loadingPrediction && !predictionData ? (
                <div className="space-y-4">
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                        {Array(10).fill(0).map((_, i) => <SkeletonCard key={i} />)}
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                        <div className="lg:col-span-2 bg-court-surface border border-court-border rounded-xl h-80 animate-pulse" />
                        <div className="space-y-4">
                            <div className="bg-court-surface border border-court-border rounded-xl h-48 animate-pulse" />
                            <div className="bg-court-surface border border-court-border rounded-xl h-28 animate-pulse" />
                        </div>
                    </div>
                </div>
            ) : errorPrediction ? (
                <div className="text-center py-12 font-mono text-sm text-red-400 border border-dashed border-red-400/20 rounded-xl">
                    Unable to generate prediction for this player.
                </div>
            ) : predictionData ? (
                <>
                    <StatCards predictions={predictionData.predictions} />

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                        <div className="lg:col-span-2 space-y-5">
                            <TrendCharts
                                history={predictionData.history}
                                predictions={predictionData.predictions}
                            />
                            <SeasonLog
                                logs={predictionData.history}
                                seasonAvgs={predictionData.predictions}
                            />
                        </div>
                        <div className="space-y-4">
                            <FantasyBreakdown predictions={predictionData.predictions} />
                            <FeatureImportance features={predictionData.feature_importance} />
                        </div>
                    </div>
                </>
            ) : (
                <div className="text-center py-12 font-mono text-sm text-court-muted border border-dashed border-court-border rounded-xl">
                    No prediction data available.
                </div>
            )}
        </div>
    );
}