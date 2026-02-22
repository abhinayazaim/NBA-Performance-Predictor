import React from 'react';
import clsx from 'clsx';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

function Delta({ val, avg, inverse = false }) {
    if (avg == null || typeof val !== 'number') return null;
    const isAbove = val > avg;
    const isGood = inverse ? !isAbove : isAbove;
    if (Math.abs(val - avg) < 0.05) return <Minus size={10} className="inline ml-0.5 text-court-muted" />;
    return isGood
        ? <ArrowUp size={10} className="inline ml-0.5 text-emerald-400" />
        : <ArrowDown size={10} className="inline ml-0.5 text-red-400" />;
}

function cell(val, avg, inverse = false) {
    if (avg == null || typeof val !== 'number') return '';
    const isAbove = val > avg;
    const isGood = inverse ? !isAbove : isAbove;
    if (Math.abs(val - avg) < 0.05) return '';
    return isGood ? 'text-emerald-400' : 'text-red-400';
}

export default function SeasonLog({ logs, seasonAvgs }) {
    if (!logs?.length) return null;
    const games = logs.slice(0, 5);
    const avgs = seasonAvgs || {};

    return (
        <div className="bg-court-surface border border-court-border rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-court-border">
                <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-court-subtext">Last 5 Games</span>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono">
                    <thead>
                        <tr className="border-b border-court-border/50">
                            {['Date', 'Matchup', 'W/L', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'FG%', 'FPTS'].map(h => (
                                <th key={h} className={clsx(
                                    'px-3 py-2.5 text-[9px] font-mono uppercase tracking-widest text-court-muted font-medium',
                                    ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG%', 'FPTS'].includes(h) ? 'text-right' : 'text-left'
                                )}>{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-court-border/30">
                        {games.map((g, i) => {
                            const isWin = g.WL === 'W';
                            const pts = typeof g.PTS === 'number' ? g.PTS : parseFloat(g.PTS) || 0;
                            const reb = typeof g.REB === 'number' ? g.REB : parseFloat(g.REB) || 0;
                            const ast = typeof g.AST === 'number' ? g.AST : parseFloat(g.AST) || 0;
                            const stl = typeof g.STL === 'number' ? g.STL : parseFloat(g.STL) || 0;
                            const blk = typeof g.BLK === 'number' ? g.BLK : parseFloat(g.BLK) || 0;
                            const fgpct = typeof g.FG_PCT === 'number' ? g.FG_PCT : parseFloat(g.FG_PCT) || 0;
                            const fpts = typeof g.FPTS === 'number' ? g.FPTS : parseFloat(g.FPTS) || 0;

                            return (
                                <tr key={i} className="hover:bg-court-bg/30 transition-colors group">
                                    <td className="px-3 py-2.5 text-court-muted whitespace-nowrap">
                                        {String(g.GAME_DATE || '').slice(0, 10)}
                                    </td>
                                    <td className="px-3 py-2.5 text-court-subtext whitespace-nowrap max-w-[120px] truncate">
                                        {g.MATCHUP || '--'}
                                    </td>
                                    <td className="px-3 py-2.5 text-center">
                                        <span className={clsx(
                                            'text-[10px] font-bold px-1.5 py-0.5 rounded',
                                            isWin ? 'text-emerald-400 bg-emerald-400/10' : 'text-red-400 bg-red-400/10'
                                        )}>{g.WL || '--'}</span>
                                    </td>
                                    <td className={clsx('px-3 py-2.5 text-right font-semibold', cell(pts, avgs?.PTS?.season_avg))}>
                                        {pts}<Delta val={pts} avg={avgs?.PTS?.season_avg} />
                                    </td>
                                    <td className={clsx('px-3 py-2.5 text-right', cell(reb, avgs?.REB?.season_avg))}>
                                        {reb}<Delta val={reb} avg={avgs?.REB?.season_avg} />
                                    </td>
                                    <td className={clsx('px-3 py-2.5 text-right', cell(ast, avgs?.AST?.season_avg))}>
                                        {ast}<Delta val={ast} avg={avgs?.AST?.season_avg} />
                                    </td>
                                    <td className={clsx('px-3 py-2.5 text-right', cell(stl, avgs?.STL?.season_avg))}>
                                        {stl}
                                    </td>
                                    <td className={clsx('px-3 py-2.5 text-right', cell(blk, avgs?.BLK?.season_avg))}>
                                        {blk}
                                    </td>
                                    <td className={clsx('px-3 py-2.5 text-right', cell(fgpct, avgs?.FG_PCT?.season_avg))}>
                                        {fgpct.toFixed(1)}%
                                    </td>
                                    <td className={clsx('px-3 py-2.5 text-right font-semibold', cell(fpts, avgs?.FPTS?.season_avg))}>
                                        {fpts.toFixed(1)}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
            <div className="px-5 py-2 border-t border-court-border/30 bg-court-bg/20">
                <p className="text-[9px] font-mono text-court-muted">
                    <span className="text-emerald-400">↑</span> above season avg &nbsp;·&nbsp;
                    <span className="text-red-400">↓</span> below season avg
                </p>
            </div>
        </div>
    );
}