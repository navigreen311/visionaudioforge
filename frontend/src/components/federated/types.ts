/** Shared types for federated learning components. */

export type RoundStatus = "complete" | "partial" | "failed";

export interface SiteUpdate {
  siteId: string;
  samplesUsed: number;
  localLoss: number;
  localAccuracy: number;
  uploadDuration: number;
}

export interface RoundData {
  round: number;
  participants: number;
  accuracy: number;
  loss: number;
  epsilonSpent: number;
  durationSeconds: number;
  status: RoundStatus;
  siteUpdates: SiteUpdate[];
}

export interface ParticipantInfo {
  id: string;
  label: string;
}
