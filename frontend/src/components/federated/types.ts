/** Shared types for federated learning charts. */

export interface RoundData {
  round_number: number;
  accuracy: number | null;
  loss: number | null;
  privacy_epsilon_spent: number;
  participants: number;
  duration_s: number | null;
}
