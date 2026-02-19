import React, { useState } from 'react';
import { Search, RotateCw } from 'lucide-react';
import { usePlayers } from '../hooks/usePlayer';
import { usePlayerContext } from '../context/PlayerContext';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';

const Navbar = () => {
    const { data: players, isLoading: loadingPlayers } = usePlayers();
    const { selectedPlayerId, setSelectedPlayerId } = usePlayerContext();
    const [query, setQuery] = useState("");
    const [showDropdown, setShowDropdown] = useState(false);

    const navigate = useNavigate();
    const location = useLocation();
    const queryClient = useQueryClient();

    const handleSelectPlayer = (player) => {
        setSelectedPlayerId(player.id);
        setQuery(player.name);
        setShowDropdown(false);

        // Navigation Logic
        if (location.pathname.startsWith('/player/')) {
            navigate(`/player/${player.id}`);
        }
    };

    const handleRefresh = () => {
        queryClient.invalidateQueries();
    };

    // Filter players
    const filtered = (players && query.length > 0)
        ? players.filter(p => p.name.toLowerCase().includes(query.toLowerCase())).slice(0, 10)
        : [];

    // Update Input if selectedPlayer changes externally (optional, but good for sync)
    // For now, let's keep input independent or sync it?
    // User asked: "When a player is selected, set the input value to their name"

    return (
        <nav className="border-b border-court-border bg-court-surface/50 backdrop-blur sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col md:flex-row justify-between items-center gap-4">
                <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                    <span className="text-2xl font-display text-court-orange tracking-widest">COURT<span className="text-court-text">VISION</span></span>
                    <span className="text-xs font-mono bg-court-border px-2 py-0.5 rounded text-court-subtext">v3.1</span>
                </Link>

                <div className="flex items-center gap-4 w-full md:w-auto z-50">
                    {/* Search / Type-to-Filter */}
                    <div className="relative group w-full md:w-64">
                        <Search className="absolute left-3 top-2.5 text-court-muted" size={16} />
                        <input
                            type="text"
                            className="w-full bg-court-bg border border-court-border rounded px-10 py-2 text-sm focus:outline-none focus:border-court-orange placeholder-court-subtext text-court-text"
                            placeholder="Search players..."
                            value={query}
                            onChange={(e) => {
                                setQuery(e.target.value);
                                setShowDropdown(true);
                            }}
                            onFocus={() => setShowDropdown(true)}
                        />

                        {showDropdown && filtered.length > 0 && (
                            <div className="absolute top-full left-0 w-full mt-1 bg-court-surface border border-court-border rounded shadow-lg max-h-60 overflow-y-auto z-50">
                                {filtered.map(p => (
                                    <div
                                        key={p.id}
                                        className="px-4 py-2 hover:bg-court-border cursor-pointer text-sm flex items-center justify-between"
                                        onClick={() => handleSelectPlayer(p)}
                                    >
                                        <span>{p.name}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleRefresh}
                        className="p-2 border border-court-border rounded bg-court-bg hover:bg-court-border transition-colors text-court-subtext hover:text-court-orange"
                        title="Refresh Data"
                    >
                        <RotateCw size={18} />
                    </button>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
