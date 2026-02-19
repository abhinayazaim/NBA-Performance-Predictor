import React from 'react';
import clsx from 'clsx';
import { RefreshCcw, ArrowUp, ArrowDown, Minus } from 'lucide-react'; // Added ArrowUp, ArrowDown, Minus

export default function SeasonLog({ logs, seasonAvgs }) {
    if (!logs || logs.length === 0) return null;

    // Helper function for trend icon
    const getTrendIcon = (value, average) => {
        if (average === undefined || average === null) return null;
        if (value > average) {
            return <ArrowUp size={12} className="inline-block ml-1 text-court-green" />;
        } else if (value < average) {
            return <ArrowDown size={12} className="inline-block ml-1 text-court-red" />;
        } else {
            return <Minus size={12} className="inline-block ml-1 text-court-subtext" />;
        }
    };

    const getCellClass = (val, statObj, inverse = false) => {
        if (!statObj || typeof val !== 'number') return '';
        const avg = statObj.season_avg;
        if (avg === undefined) return '';

        let isGood = val >= avg;
        if (inverse) isGood = !isGood;
        return isGood ? 'text-court-green bg-court-green/5' : 'text-court-red bg-court-red/5';
    };

    return (
        <div className="bg-court-surface border border-court-border rounded-lg p-6 overflow-hidden">
            <h3 className="text-court-orange text-xs font-bold uppercase tracking-widest mb-4">
                LAST 5 GAMES
            </h3>

            <div className="overflow-x-auto">
                <table className="w-full text-sm font-mono text-left">
                    <thead className="bg-court-bg text-court-subtext border-b border-court-border">
                        <tr>
                            <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs">Date</th>
                            <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs">Versus</th>
                            <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-center">W/L</th>
                            <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">PTS</th>
                            <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">REB</th>
                            <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">AST</th>
                            <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">STL</th>
                            <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">BLK</th>
                            <th className="px-4 py-3 font-medium uppercase tracking-wider text-xs text-right">FPTS</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-court-border">
                        {(logs || []).slice(0, 5).map((game, idx) => {
                            const isWin = game.WL === 'W';
                            return (
                                <tr key={idx} className="hover:bg-court-bg/50 transition-colors">
                                    <td className="px-4 py-3 text-court-subtext whitespace-nowrap">{game.GAME_DATE}</td>
                                    <td className="px-4 py-3 whitespace-nowrap">{game.MATCHUP}</td>
                                    <td className={clsx("px-4 py-3 text-center font-bold", isWin ? "text-court-green" : "text-court-red")}>
                                        {game.WL}
                                    </td>
                                    <td className="px-4 py-3 text-right font-medium text-white">
                                        {game.PTS}
                                        {getTrendIcon(game.PTS, seasonAvgs?.PTS?.season_avg)}
                                    </td>
                                    <td className="px-4 py-3 text-right text-court-text">
                                        {game.REB}
                                        {getTrendIcon(game.REB, seasonAvgs?.REB?.season_avg)}
                                    </td>
                                    <td className="px-4 py-3 text-right text-court-text">
                                        {game.AST}
                                    </td>
                                    <td className={clsx("px-4 py-3 text-right font-medium", getCellClass(game.STL, seasonAvgs.STL))}>
                                        {game.STL}
                                    </td>
                                    <td className={clsx("px-4 py-3 text-right font-medium", getCellClass(game.BLK, seasonAvgs.BLK))}>
                                        {game.BLK}
                                    </td>
                                    <td className={clsx("px-4 py-3 text-right font-medium", getCellClass(game.TOV, seasonAvgs.TOV, true))}>
                                        {game.TOV}
                                    </td>
                                    <td className={clsx("px-4 py-3 text-right font-medium", getCellClass(game.FG_PCT, seasonAvgs.FG_PCT))}>
                                        {game.FG_PCT.toFixed(1)}%
                                    </td>
                                    <td className={clsx("px-4 py-3 text-right font-medium", getCellClass(game.FT_PCT, seasonAvgs.FT_PCT))}>
                                        {game.FT_PCT.toFixed(1)}%
                                    </td>
                                    <td className={clsx("px-4 py-3 text-right font-medium", getCellClass(game.FG3M, seasonAvgs.FG3M))}>
                                        {game.FG3M}
                                    </td>
                                    <td className={clsx("px-4 py-3 text-right font-bold", getCellClass(game.FPTS, seasonAvgs.FPTS))}>
                                        {game.FPTS.toFixed(1)}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
