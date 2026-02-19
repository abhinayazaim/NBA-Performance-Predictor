import React from 'react';
import { usePlayerContext } from '../context/PlayerContext';
import { usePlayerProfile, usePlayerPrediction } from '../hooks/usePlayer';
import PlayerHeader from '../components/PlayerHeader';
import StatCards from '../components/StatCards';
import TrendCharts from '../components/TrendCharts';
import SeasonLog from '../components/SeasonLog';
import FantasyBreakdown from '../components/FantasyBreakdown';
import FeatureImportance from '../components/FeatureImportance';
import { Loader2 } from 'lucide-react';

const QUICK_PICKS = [
    { id: 2544, name: 'LeBron James' },
    { id: 201939, name: 'Stephen Curry' },
    { id: 203999, name: 'Nikola Jokic' },
    { id: 203507, name: 'Giannis Antetokounmpo' },
    { id: 1629029, name: 'Luka Doncic' },
];

export default function Dashboard() {
    const { selectedPlayerId, setSelectedPlayerId } = usePlayerContext();

    // Queries
    const { data: profile, isLoading: loadingProfile, error: errorProfile } = usePlayerProfile(selectedPlayerId);
    const { data: predictionData, isLoading: loadingPrediction, error: errorPrediction } = usePlayerPrediction(selectedPlayerId);

    // Empty State
    if (!selectedPlayerId) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 animate-in fade-in duration-500">
                <div className="text-6xl font-display tracking-widest text-court-border select-none">COURTVISION</div>
                <p className="text-court-subtext font-mono text-sm tracking-widest text-center">
                    SEARCH A PLAYER TO GENERATE AI PREDICTIONS
                </p>
                <div className="flex gap-3 mt-4 flex-wrap justify-center">
                    {QUICK_PICKS.map(p => (
                        <button
                            key={p.id}
                            onClick={() => setSelectedPlayerId(p.id)}
                            className="border border-court-border hover:border-court-orange text-court-subtext hover:text-court-text 
                                       font-mono text-xs px-4 py-2 rounded transition-all duration-200"
                        >
                            {p.name}
                        </button>
                    ))}
                </div>
            </div>
        );
    }

    // Step 3: Visible Loading/Error States
    if (loadingProfile && !profile) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-court-subtext">
                <Loader2 size={32} className="animate-spin mb-4 text-court-orange" />
                <p className="font-mono text-sm animate-pulse">Scouting Player Data...</p>
            </div>
        );
    }

    if (errorProfile) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-court-red">
                <p>Error loading player profile</p>
                <button onClick={() => setSelectedPlayerId(null)} className="underline mt-2">Clear Selection</button>
            </div>
        );
    }

    return (
        <div className="space-y-6 opacity-0 animate-[fadeIn_0.5s_ease-out_forwards]">
            <PlayerHeader profile={profile} />

            {loadingPrediction && !predictionData ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-64 animate-pulse">
                    <div className="bg-court-surface rounded-lg border border-court-border h-64"></div>
                    <div className="bg-court-surface rounded-lg border border-court-border h-64"></div>
                </div>
            ) : errorPrediction ? (
                <div className="text-center py-12 text-court-red border border-dashed border-court-red/30 rounded-lg">
                    Unable to generate prediction.
                </div>
            ) : (predictionData ? (
                <>
                    <StatCards predictions={predictionData?.predictions} />

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2 space-y-6">
                            <TrendCharts
                                history={predictionData?.history}
                                predictions={predictionData?.predictions}
                            />
                            <SeasonLog
                                logs={predictionData?.history}
                                seasonAvgs={predictionData?.predictions?.PTS?.season_avg ? predictionData.predictions : {}}
                            />
                        </div>
                        <div className="space-y-6">
                            <FantasyBreakdown predictions={predictionData?.predictions} />
                            <FeatureImportance features={predictionData?.feature_importance} />
                        </div>
                    </div>
                </>
            ) : (
                <div className="text-center py-12 text-court-muted border border-dashed border-court-border rounded-lg">
                    No prediction data available for this player.
                </div>
            ))}
        </div>
    );
}
