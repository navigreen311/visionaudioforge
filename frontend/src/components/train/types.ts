/** Shared types for the training / experiments feature. */

export interface EpochData {
  epoch_number: number;
  train_loss: number | null;
  val_loss: number | null;
  train_acc: number | null;
  val_acc: number | null;
  lr: number | null;
  duration_s: number | null;
}

export type ExperimentStatus = "running" | "completed" | "failed" | "cancelled";

export interface Experiment {
  id: string;
  name: string;
  model: string;
  status: ExperimentStatus;
  best_val_loss: number | null;
  best_epoch: number | null;
  duration: string | null;
  config: {
    epochs: number;
    learning_rate: number;
    batch_size: number;
  };
  epochs: EpochData[];
  error_message: string | null;
  created_at: string;
}

export interface ExperimentCreatePayload {
  name: string;
  model: string;
  epochs: number;
  learning_rate: number;
  batch_size: number;
}
