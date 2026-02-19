import React from 'react';
import { User, Calendar, Hash } from 'lucide-react';
import { Link } from 'react-router-dom';
import { usePlayerIntel } from '../hooks/usePlayer';
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

// Inlined PlayerIntel to avoid import chain issues
function PlayerIntel({ playerId }) {
    const { data: intel, isLoading } = usePlayerIntel(playerId);
    const [isOpen, setIsOpen] = React.useState(false);

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
                <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
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
}

export default function PlayerHeader({ profile }) {
    if (!profile) return null;

    const { bio, headshot_url, next_game, key_matchup } = profile;
    if (!bio) return null;

    const playerId = bio?.PERSON_ID;

    return (
        <div className="bg-court-surface border-b border-court-border p-6 mb-6">
            <div className="flex flex-col md:flex-row gap-8 items-center md:items-start max-w-7xl mx-auto">

                {/* Headshot */}
                <Link
                    to={`/player/${playerId}`}
                    className="relative w-40 h-40 md:w-48 md:h-48 shrink-0 bg-court-bg rounded-lg border border-court-border overflow-hidden flex items-center justify-center hover:opacity-90 transition-opacity cursor-pointer shadow-lg group"
                >
                    {headshot_url ? (
                        <>
                            <img
                                src={headshot_url}
                                alt={bio?.DISPLAY_FIRST_LAST}
                                className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500"
                                onError={(e) => {
                                    e.target.style.display = 'none';
                                    e.target.nextSibling.style.display = 'flex';
                                }}
                            />
                            <div className="absolute inset-0 items-center justify-center hidden">
                                <User className="w-24 h-24 text-court-subtext" />
                            </div>
                        </>
                    ) : (
                        <User className="w-24 h-24 text-court-subtext" />
                    )}
                </Link>

                {/* Bio */}
                <div className="flex-1 text-center md:text-left">
                    <Link to={`/player/${playerId}`} className="hover:text-court-orange transition-colors">
                        <h1 className="text-5xl font-display text-court-text uppercase mb-2">
                            {bio?.DISPLAY_FIRST_LAST || 'Unknown Player'}
                        </h1>
                    </Link>

                    <div className="flex flex-wrap justify-center md:justify-start gap-4 mb-6">
                        <span className="flex items-center gap-2 bg-court-bg px-3 py-1 rounded border border-court-border text-court-subtext font-mono text-sm">
                            <Hash size={14} /> {bio?.JERSEY || '--'}
                        </span>
                        <span className="bg-court-bg px-3 py-1 rounded border border-court-border text-court-orange font-bold tracking-wider text-sm">
                            {bio?.POSITION || '--'}
                        </span>
                        <span className="text-court-text font-medium text-lg">
                            {bio?.TEAM_NAME} <span className="text-court-subtext">({bio?.TEAM_ABBREVIATION})</span>
                        </span>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-court-subtext text-sm font-mono border-t border-court-border pt-4">
                        <div>
                            <span className="block text-xs uppercase tracking-widest text-court-muted mb-1">Height/Weight</span>
                            {bio?.HEIGHT} / {bio?.WEIGHT}
                        </div>
                        <div>
                            <span className="block text-xs uppercase tracking-widest text-court-muted mb-1">Experience</span>
                            {bio?.SEASON_EXP} Years
                        </div>
                        <div>
                            <span className="block text-xs uppercase tracking-widest text-court-muted mb-1">Country</span>
                            {bio?.COUNTRY}
                        </div>
                        <div>
                            <span className="block text-xs uppercase tracking-widest text-court-muted mb-1">Draft</span>
                            {bio?.DRAFT_YEAR} (R{bio?.DRAFT_ROUND} P{bio?.DRAFT_NUMBER})
                        </div>
                    </div>

                    {playerId && <PlayerIntel playerId={playerId} />}
                </div>

                {/* Next Game */}
                <div className="w-full md:w-72 bg-court-bg border border-court-border rounded-lg p-4">
                    <h3 className="text-court-orange text-xs font-bold uppercase tracking-widest mb-3 flex items-center gap-2">
                        <Calendar size={14} /> Next Matchup
                    </h3>
                    {next_game ? (
                        <div>
                            {/* Opponent team */}
                            <div className="text-xl md:text-2xl font-display text-court-text mb-1">
                                {next_game.is_home ? 'vs' : '@'} {next_game.opp_abbreviation || next_game.opp_name || 'Opponent'}
                            </div>
                            <div className="text-court-subtext font-mono text-xs mb-3">
                                {next_game.date} · {next_game.is_home ? 'HOME' : 'AWAY'}
                            </div>

                            {/* Key matchup player */}
                            {key_matchup && (
                                <div className="border-t border-court-border pt-3">
                                    <div className="text-court-muted font-mono text-xs uppercase tracking-widest mb-2">
                                        Key Matchup
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <img
                                            src={key_matchup.headshot_url}
                                            alt={key_matchup.name}
                                            className="w-10 h-10 rounded-full object-cover object-top border border-court-border bg-court-surface"
                                            onError={(e) => { e.target.style.display = 'none' }}
                                        />
                                        <div>
                                            <div className="text-court-text font-semibold text-sm truncate w-32">
                                                {key_matchup.name}
                                            </div>
                                            <div className="text-court-subtext font-mono text-xs">
                                                {key_matchup.position} · #{key_matchup.jersey}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="text-court-subtext font-mono text-sm italic">TBD</div>
                    )}
                </div>

            </div>
        </div>
    );
}