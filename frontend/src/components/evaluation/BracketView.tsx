"use client";

import React from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MatchupData {
  model_a: string;
  model_b: string;
  winner: string;
  score_a: number;
  score_b: number;
}

export interface MatchupRound {
  round: number;
  label: string;
  matchups: MatchupData[];
}

interface BracketViewProps {
  rounds: MatchupRound[];
  winner: string;
}

// ---------------------------------------------------------------------------
// Layout constants
// ---------------------------------------------------------------------------

const PILL_W = 160;
const PILL_H = 28;
const PILL_GAP = 8;
const MATCHUP_H = PILL_H * 2 + PILL_GAP;
const ROUND_GAP = 80;
const VERTICAL_PADDING = 24;
const HEADER_H = 28;
const CROWN_AREA = 100;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getMatchupY(
  matchupIdx: number,
  totalMatchups: number,
  canvasContentH: number,
): number {
  if (totalMatchups === 1) {
    return canvasContentH / 2 - MATCHUP_H / 2;
  }
  const slotH = canvasContentH / totalMatchups;
  return slotH * matchupIdx + (slotH - MATCHUP_H) / 2;
}

function pillFill(isWinner: boolean): string {
  return isWinner ? "#dcfce7" : "#f3f4f6";
}

function pillStroke(isWinner: boolean): string {
  return isWinner ? "#16a34a" : "#d1d5db";
}

function nameColor(isWinner: boolean): string {
  return isWinner ? "#15803d" : "#9ca3af";
}

function scoreColor(isWinner: boolean): string {
  return isWinner ? "#15803d" : "#6b7280";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function BracketView({ rounds, winner }: BracketViewProps) {
  if (!rounds.length) return null;

  const firstRoundMatchups = rounds[0].matchups.length;
  const canvasContentH = Math.max(
    firstRoundMatchups * (MATCHUP_H + VERTICAL_PADDING * 2),
    200,
  );
  const totalH = canvasContentH + HEADER_H + VERTICAL_PADDING * 2;
  const totalW =
    rounds.length * (PILL_W + ROUND_GAP) + CROWN_AREA;

  return (
    <svg
      viewBox={`0 0 ${totalW} ${totalH}`}
      className="w-full"
      style={{ minHeight: 300 }}
      role="img"
      aria-label="Tournament bracket"
    >
      {/* Round headers */}
      {rounds.map((round, ri) => {
        const x = ri * (PILL_W + ROUND_GAP) + PILL_W / 2;
        return (
          <text
            key={`header-${ri}`}
            x={x}
            y={HEADER_H - 6}
            textAnchor="middle"
            fontSize={12}
            fontWeight={600}
            fill="#6b7280"
          >
            {round.label}
          </text>
        );
      })}

      {/* Rounds */}
      {rounds.map((round, ri) => {
        const roundX = ri * (PILL_W + ROUND_GAP);
        const matchupsInRound = round.matchups.length;

        return (
          <g key={`round-${ri}`}>
            {round.matchups.map((m, mi) => {
              const my =
                getMatchupY(mi, matchupsInRound, canvasContentH) +
                HEADER_H +
                VERTICAL_PADDING;
              const isWinnerA = m.winner === m.model_a;
              const isWinnerB = m.winner === m.model_b;

              // Connector to next round
              const nextRound = rounds[ri + 1];
              let connectorPath: string | null = null;

              if (nextRound) {
                const outX = roundX + PILL_W;
                const outY = my + MATCHUP_H / 2;
                const nextRoundX = (ri + 1) * (PILL_W + ROUND_GAP);
                const nextMi = Math.floor(mi / 2);
                const nextMatchups = nextRound.matchups.length;
                const nextMy =
                  getMatchupY(nextMi, nextMatchups, canvasContentH) +
                  HEADER_H +
                  VERTICAL_PADDING;
                const targetY =
                  mi % 2 === 0
                    ? nextMy + PILL_H / 2
                    : nextMy + PILL_H + PILL_GAP + PILL_H / 2;

                const midX = outX + ROUND_GAP / 2;
                connectorPath = `M ${outX} ${outY} H ${midX} V ${targetY} H ${nextRoundX}`;
              }

              const truncate = (s: string, max: number) =>
                s.length > max ? s.slice(0, max - 2) + ".." : s;

              return (
                <g key={`matchup-${ri}-${mi}`}>
                  {/* --- Model A pill --- */}
                  <rect
                    x={roundX}
                    y={my}
                    width={PILL_W}
                    height={PILL_H}
                    rx={6}
                    fill={pillFill(isWinnerA)}
                    stroke={pillStroke(isWinnerA)}
                    strokeWidth={1.5}
                  />
                  <text
                    x={roundX + 10}
                    y={my + PILL_H / 2 + 1}
                    dominantBaseline="middle"
                    fontSize={11}
                    fontWeight={isWinnerA ? 700 : 400}
                    fill={nameColor(isWinnerA)}
                    textDecoration={!isWinnerA ? "line-through" : undefined}
                  >
                    {truncate(m.model_a, 16)}
                  </text>
                  <text
                    x={roundX + PILL_W - 10}
                    y={my + PILL_H / 2 + 1}
                    dominantBaseline="middle"
                    textAnchor="end"
                    fontSize={10}
                    fontFamily="monospace"
                    fill={scoreColor(isWinnerA)}
                  >
                    {m.score_a.toFixed(3)}
                  </text>

                  {/* --- Model B pill --- */}
                  <rect
                    x={roundX}
                    y={my + PILL_H + PILL_GAP}
                    width={PILL_W}
                    height={PILL_H}
                    rx={6}
                    fill={pillFill(isWinnerB)}
                    stroke={pillStroke(isWinnerB)}
                    strokeWidth={1.5}
                  />
                  <text
                    x={roundX + 10}
                    y={my + PILL_H + PILL_GAP + PILL_H / 2 + 1}
                    dominantBaseline="middle"
                    fontSize={11}
                    fontWeight={isWinnerB ? 700 : 400}
                    fill={nameColor(isWinnerB)}
                    textDecoration={!isWinnerB ? "line-through" : undefined}
                  >
                    {truncate(m.model_b, 16)}
                  </text>
                  <text
                    x={roundX + PILL_W - 10}
                    y={my + PILL_H + PILL_GAP + PILL_H / 2 + 1}
                    dominantBaseline="middle"
                    textAnchor="end"
                    fontSize={10}
                    fontFamily="monospace"
                    fill={scoreColor(isWinnerB)}
                  >
                    {m.score_b.toFixed(3)}
                  </text>

                  {/* Connector line */}
                  {connectorPath && (
                    <path
                      d={connectorPath}
                      fill="none"
                      stroke="#d1d5db"
                      strokeWidth={1.5}
                    />
                  )}
                </g>
              );
            })}
          </g>
        );
      })}

      {/* Crown for champion */}
      {winner &&
        (() => {
          const lastRoundX =
            (rounds.length - 1) * (PILL_W + ROUND_GAP) + PILL_W;
          const lastMy =
            getMatchupY(0, 1, canvasContentH) +
            HEADER_H +
            VERTICAL_PADDING;
          const crownX = lastRoundX + ROUND_GAP / 2 + 10;
          const crownY = lastMy + MATCHUP_H / 2;
          return (
            <g>
              <text
                x={crownX}
                y={crownY - 14}
                textAnchor="middle"
                fontSize={24}
              >
                &#9733;
              </text>
              <text
                x={crownX}
                y={crownY + 8}
                textAnchor="middle"
                fontSize={12}
                fontWeight={700}
                fill="#15803d"
              >
                {winner}
              </text>
            </g>
          );
        })()}
    </svg>
  );
}
