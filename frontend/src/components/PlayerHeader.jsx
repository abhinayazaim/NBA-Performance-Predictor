import React from 'react';
import { User, Calendar, Hash, MapPin, Ruler, Shield } from 'lucide-react';
import { Link } from 'react-router-dom';
import { usePlayerIntel } from '../hooks/usePlayer';
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

function PlayerIntel({ playerId }) {
    const { data: intel, isLoading } = usePlayerIntel(playerId);
    const [isOpen, setIsOpen] = React.useState(false);
    if (isLoading || !intel?.facts?.length) return null;
    return (
        <div className="mt-4 border border-court-border rounded-lg overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between px-4 py-2.5 bg-court-bg/40 hover:bg-court-bg/70 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <Sparkles size={13} className="text-court-orange" />
                    <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-court-subtext">Player Intel</span>
                </div>
                {isOpen ? <ChevronUp size={13} className="text-court-muted" /> : <ChevronDown size={13} className="text-court-muted" />}
            </button>
            {isOpen && (
                <div className="p-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 bg-court-bg/20">
                    {intel.facts.map((fact, idx) => (
                        <div key={idx} className="flex items-baseline gap-2 px-3 py-2 border border-court-border/50 rounded bg-court-bg/50">
                            <span className="text-[9px] font-mono uppercase tracking-widest text-court-muted shrink-0">{fact.label}</span>
                            <span className="text-xs font-mono text-court-text truncate font-medium" title={fact.value}>{fact.value}</span>
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
        <div className="bg-court-surface border border-court-border rounded-xl overflow-hidden mb-2">
            <div className="h-[2px] bg-court-orange w-full" />
            <div className="p-6">
                <div className="flex flex-col md:flex-row gap-6 items-start">

                    {/* Headshot */}
                    <Link to={`/player/${playerId}`}
                        className="relative shrink-0 w-28 h-28 md:w-36 md:h-36 rounded-xl border border-court-border overflow-hidden
                                   bg-court-bg group hover:border-court-orange transition-all duration-300 shadow-lg">
                        <img
                            src={headshot_url}
                            alt={bio?.DISPLAY_FIRST_LAST}
                            className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500"
                            onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                        />
                        <div className="absolute inset-0 items-center justify-center hidden bg-court-bg">
                            <User className="w-16 h-16 text-court-border" />
                        </div>
                    </Link>

                    {/* Bio */}
                    <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                            <span className="text-[10px] font-mono bg-court-orange/10 text-court-orange border border-court-orange/20 px-2 py-0.5 rounded tracking-widest uppercase">
                                {bio?.POSITION || '--'}
                            </span>
                            <span className="text-[10px] font-mono text-court-muted flex items-center gap-1">
                                <Hash size={9} />{bio?.JERSEY || '--'}
                            </span>
                            {bio?.GREATEST_75_FLAG === 'Y' && (
                                <span className="text-[9px] font-mono bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 px-2 py-0.5 rounded tracking-widest">
                                    75TH ANNIVERSARY
                                </span>
                            )}
                        </div>

                        <Link to={`/player/${playerId}`} className="group">
                            <h1 className="text-3xl md:text-5xl font-display text-court-text uppercase leading-none mb-1 group-hover:text-court-orange transition-colors duration-200">
                                {bio?.DISPLAY_FIRST_LAST || 'Unknown Player'}
                            </h1>
                        </Link>

                        <p className="text-court-subtext font-mono text-sm mb-4">
                            {bio?.TEAM_CITY} <span className="text-court-text font-semibold">{bio?.TEAM_NAME}</span>
                            <span className="text-court-border mx-2">·</span>
                            <span className="text-court-muted">{bio?.TEAM_ABBREVIATION}</span>
                        </p>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            {[
                                { label: 'Size', value: `${bio?.HEIGHT} / ${bio?.WEIGHT}lbs` },
                                { label: 'Experience', value: `${bio?.SEASON_EXP} seasons` },
                                { label: 'Country', value: bio?.COUNTRY },
                                { label: 'Draft', value: bio?.DRAFT_YEAR ? `${bio.DRAFT_YEAR} · R${bio.DRAFT_ROUND} P${bio.DRAFT_NUMBER}` : 'Undrafted' },
                            ].map((item, i) => (
                                <div key={i} className="bg-court-bg/50 border border-court-border/50 rounded-lg px-3 py-2">
                                    <span className="block text-[9px] font-mono uppercase tracking-widest text-court-muted mb-0.5">{item.label}</span>
                                    <span className="text-xs font-mono text-court-subtext">{item.value}</span>
                                </div>
                            ))}
                        </div>

                        <PlayerIntel playerId={playerId} />
                    </div>

                    {/* Next Matchup */}
                    <div className="w-full md:w-52 shrink-0 bg-court-bg border border-court-border rounded-xl overflow-hidden">
                        <div className="px-4 py-2.5 border-b border-court-border flex items-center gap-2">
                            <Calendar size={11} className="text-court-orange" />
                            <span className="text-[10px] font-mono uppercase tracking-widest text-court-orange font-bold">Next Matchup</span>
                        </div>
                        {next_game ? (
                            <div className="p-4">
                                <div className="text-2xl font-display text-court-text leading-none mb-0.5">
                                    {next_game.is_home ? 'vs' : '@'} {next_game.opp_abbreviation || '---'}
                                </div>
                                <div className="text-[10px] font-mono text-court-muted mb-1 truncate">{next_game.opp_name}</div>
                                <div className="flex items-center gap-2 mb-4">
                                    <span className="text-[10px] font-mono text-court-subtext">{next_game.date}</span>
                                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold font-mono ${next_game.is_home ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'}`}>
                                        {next_game.is_home ? 'HOME' : 'AWAY'}
                                    </span>
                                </div>
                                {key_matchup && (
                                    <div className="border-t border-court-border/50 pt-3">
                                        <div className="text-[9px] font-mono uppercase tracking-widest text-court-muted mb-2">Key Matchup</div>
                                        <div className="flex items-center gap-2.5">
                                            <img
                                                src={key_matchup.headshot_url}
                                                alt={key_matchup.name}
                                                className="w-9 h-9 rounded-full object-cover object-top border border-court-border bg-court-surface shrink-0"
                                                onError={(e) => { e.target.style.display = 'none'; }}
                                            />
                                            <div className="min-w-0">
                                                <div className="text-xs font-mono font-semibold text-court-text truncate">{key_matchup.name}</div>
                                                <div className="text-[10px] font-mono text-court-muted">{key_matchup.position} · #{key_matchup.jersey}</div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="p-4 text-court-muted font-mono text-xs italic">No upcoming game found</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}