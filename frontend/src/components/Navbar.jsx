import React, { useState, useRef, useEffect } from 'react';
import { Search, RotateCw, X } from 'lucide-react';
import { usePlayers } from '../hooks/usePlayer';
import { usePlayerContext } from '../context/PlayerContext';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';

const Navbar = () => {
    const { data: players, isLoading: loadingPlayers } = usePlayers();
    const { selectedPlayerId, setSelectedPlayerId } = usePlayerContext();
    const [query, setQuery] = useState('');
    const [showDropdown, setShowDropdown] = useState(false);
    const [spinning, setSpinning] = useState(false);
    const inputRef = useRef(null);
    const dropdownRef = useRef(null);

    const navigate = useNavigate();
    const location = useLocation();
    const queryClient = useQueryClient();

    // Close dropdown on outside click
    useEffect(() => {
        const handler = (e) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
                setShowDropdown(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    const handleSelectPlayer = (player) => {
        setSelectedPlayerId(player.id);
        setQuery(player.name);
        setShowDropdown(false);
        inputRef.current?.blur();
        if (location.pathname.startsWith('/player/')) {
            navigate(`/player/${player.id}`);
        }
    };

    const handleRefresh = () => {
        setSpinning(true);
        queryClient.invalidateQueries();
        setTimeout(() => setSpinning(false), 800);
    };

    const handleClear = () => {
        setQuery('');
        setSelectedPlayerId(null);
        inputRef.current?.focus();
    };

    const filtered = (players && query.length > 0)
        ? players.filter(p => p.name.toLowerCase().includes(query.toLowerCase())).slice(0, 8)
        : [];

    return (
        <nav className="border-b border-court-border bg-court-bg/80 backdrop-blur-md sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-6 py-3 flex justify-between items-center gap-6">

                {/* Logo */}
                <Link to="/" onClick={() => setSelectedPlayerId(null)} className="flex items-center gap-3 shrink-0 group">
                    <div className="flex items-center">
                        <span className="text-xl font-display text-court-orange tracking-[0.2em] group-hover:tracking-[0.25em] transition-all duration-300">COURT</span>
                        <span className="text-xl font-display text-court-text tracking-[0.2em]">VISION</span>
                    </div>
                    <span className="text-[10px] font-mono bg-court-border/60 border border-court-border px-2 py-0.5 rounded text-court-muted tracking-widest">
                        v3.1
                    </span>
                </Link>

                {/* Search */}
                <div className="relative w-full max-w-sm" ref={dropdownRef}>
                    <div className="relative flex items-center">
                        <Search
                            size={14}
                            className="absolute left-3 text-court-muted pointer-events-none"
                        />
                        <input
                            ref={inputRef}
                            type="text"
                            className="w-full bg-court-surface border border-court-border rounded-lg pl-9 pr-9 py-2 text-sm font-mono
                                       text-court-text placeholder-court-muted
                                       focus:outline-none focus:border-court-orange focus:bg-court-bg
                                       transition-all duration-200"
                            placeholder={loadingPlayers ? 'Loading players...' : 'Search players...'}
                            value={query}
                            onChange={(e) => { setQuery(e.target.value); setShowDropdown(true); }}
                            onFocus={() => query.length > 0 && setShowDropdown(true)}
                            onKeyDown={(e) => {
                                if (e.key === 'Escape') { setShowDropdown(false); inputRef.current?.blur(); }
                                if (e.key === 'Enter' && filtered.length > 0) handleSelectPlayer(filtered[0]);
                            }}
                        />
                        {query && (
                            <button onClick={handleClear} className="absolute right-3 text-court-muted hover:text-court-text transition-colors">
                                <X size={14} />
                            </button>
                        )}
                    </div>

                    {/* Dropdown */}
                    {showDropdown && filtered.length > 0 && (
                        <div className="absolute top-full left-0 right-0 mt-1.5 bg-court-surface border border-court-border rounded-lg shadow-2xl overflow-hidden z-50">
                            {filtered.map((p, i) => (
                                <button
                                    key={p.id}
                                    className="w-full px-4 py-2.5 flex items-center gap-3 hover:bg-court-border/50 transition-colors text-left group"
                                    onClick={() => handleSelectPlayer(p)}
                                >
                                    <img
                                        src={`https://cdn.nba.com/headshots/nba/latest/1040x760/${p.id}.png`}
                                        alt=""
                                        className="w-7 h-7 rounded-full object-cover object-top border border-court-border bg-court-bg shrink-0"
                                        onError={(e) => { e.target.style.display = 'none'; }}
                                    />
                                    <span className="text-sm font-mono text-court-text group-hover:text-court-orange transition-colors">
                                        {p.name}
                                    </span>
                                    {i === 0 && (
                                        <span className="ml-auto text-[9px] font-mono text-court-muted bg-court-border px-1.5 py-0.5 rounded">
                                            ENTER
                                        </span>
                                    )}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Refresh */}
                <button
                    onClick={handleRefresh}
                    className="p-2 border border-court-border rounded-lg bg-court-surface hover:border-court-orange hover:text-court-orange
                               text-court-muted transition-all duration-200 shrink-0"
                    title="Refresh Data"
                >
                    <RotateCw size={15} className={spinning ? 'animate-spin' : ''} />
                </button>
            </div>
        </nav>
    );
};

export default Navbar;