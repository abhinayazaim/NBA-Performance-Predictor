import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { usePlayerProfile, usePlayerCareer } from '../hooks/usePlayer';
import PlayerHeader from '../components/PlayerHeader';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { BarChart, Bar, XAxis, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';

const CareerChart = ({ data, dataKey, color, label }) => (
    <div className="bg-court-surface border border-court-border rounded-lg p-4 flex-1 min-w-[200px]">
        <h4 className="text-court-subtext text-xs uppercase tracking-widest mb-2">{label}</h4>
        <div className="h-32">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data}>
                    <XAxis dataKey="SEASON_ID" hide />
                    <RechartsTooltip
                        contentStyle={{ backgroundColor: '#0F1520', borderColor: '#1A2235', color: '#E2E8F0' }}
                        cursor={{ fill: 'transparent' }}
                    />
                    <Bar dataKey={dataKey} fill={color} radius={[2, 2, 0, 0]} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    </div>
);

export default function PlayerCareerPage() {
    const { playerId } = useParams();
    const navigate = useNavigate();

    // Fix C: Ensure playerId is handled correctly (though fetchers should handle string/int)
    const playerIdInt = parseInt(playerId, 10);

    const { data: profile, isLoading: loadingProfile, error: errorProfile } = usePlayerProfile(playerId);
    const { data: career, isLoading: loadingCareer, error: errorCareer } = usePlayerCareer(playerId);

    const loading = loadingProfile || loadingCareer;
    const error = errorProfile || errorCareer;

    // Step 3: Visible Loading/Error States
    if (loading && !profile) {
        return (
            <div className="flex flex-col items-center justify-center h-[50vh] text-court-subtext">
                <Loader2 size={32} className="animate-spin mb-4 text-court-orange" />
                <p className="font-mono text-sm animate-pulse">Loading Career Data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-[50vh] text-court-red">
                <p className="font-mono text-lg mb-2">Error Loading Data</p>
                <p className="font-mono text-sm text-court-subtext">{error.message || 'Unknown error occurred'}</p>
                <button
                    onClick={() => navigate('/')}
                    className="mt-4 px-4 py-2 border border-court-border rounded hover:bg-court-bg/50 transition-colors text-court-text"
                >
                    Return to Dashboard
                </button>
            </div>
        );
    }

    if (!profile) return null; // Should be caught by loading/error above, but safe guard

    return (
        <div className="space-y-6 opacity-0 animate-[fadeIn_0.5s_ease-out_forwards]">
            <button
                onClick={() => navigate(-1)}
                className="flex items-center gap-2 text-court-subtext hover:text-court-orange transition-colors font-mono text-xs uppercase tracking-widest"
            >
                <ArrowLeft size={16} /> Back
            </button>

            <PlayerHeader profile={profile} />

            {/* Career Averages Charts */}
            {career && career.length > 0 ? (
                <div className="flex flex-col md:flex-row gap-4">
                    <CareerChart data={career} dataKey="PPG" color="#FF7A00" label="Points Per Game" />
                    <CareerChart data={career} dataKey="RPG" color="#38BDF8" label="Rebounds Per Game" />
                    <CareerChart data={career} dataKey="APG" color="#34D399" label="Assists Per Game" />
                </div>
            ) : (
                <div className="text-center py-8 text-court-subtext font-mono text-sm border border-dashed border-court-border rounded-lg">
                    No career chart data available.
                </div>
            )}

            {/* Career Table */}
            <div className="bg-court-surface border border-court-border rounded-lg p-6 overflow-hidden">
                <h3 className="text-court-orange text-xs font-bold uppercase tracking-widest mb-4">
                    Career Stats
                </h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm font-mono text-left">
                        <thead className="bg-court-bg text-court-subtext border-b border-court-border">
                            <tr>
                                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs">Season</th>
                                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs">Team</th>
                                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">GP</th>
                                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">MPG</th>
                                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">PPG</th>
                                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">RPG</th>
                                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">APG</th>
                                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">SPG</th>
                                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">BPG</th>
                                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">FG%</th>
                                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">FT%</th>
                                <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">3P%</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-court-border">
                            {(career || []).map((season, idx) => (
                                <tr key={idx} className="hover:bg-court-bg/50 transition-colors">
                                    <td className="px-4 py-3 text-court-subtext">{season.SEASON_ID}</td>
                                    <td className="px-4 py-3">{season.TEAM_ABBREVIATION}</td>
                                    <td className="px-4 py-3 text-right text-court-subtext">{season.GP}</td>
                                    <td className="px-4 py-3 text-right text-court-subtext">{season.MPG}</td>
                                    <td className="px-4 py-3 text-right font-medium text-white">{season.PPG}</td>
                                    <td className="px-4 py-3 text-right font-medium text-court-text">{season.RPG}</td>
                                    <td className="px-4 py-3 text-right font-medium text-court-text">{season.APG}</td>
                                    <td className="px-4 py-3 text-right text-court-subtext">{season.SPG}</td>
                                    <td className="px-4 py-3 text-right text-court-subtext">{season.BPG}</td>
                                    <td className="px-4 py-3 text-right text-court-subtext">{season.FG_PCT}%</td>
                                    <td className="px-4 py-3 text-right text-court-subtext">{season.FT_PCT}%</td>
                                    <td className="px-4 py-3 text-right text-court-subtext">{season.FG3_PCT}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
