export interface Point {
  x: number
  y: number
}

export interface Detection {
  id: string
  class_id: number
  class_name: string
  confidence: number
  box: {
    cx: number
    cy: number
    width: number
    height: number
    angle_rad: number
    angle_deg: number
    polygon: Point[]
  }
}

export interface InferenceResult {
  id: string
  created_at: string
  image_url: string
  image_width: number
  image_height: number
  elapsed_ms: number
  model_name: string
  thresholds: Record<string, number>
  detections: Detection[]
}

export interface SystemStatus {
  api: 'ready'
  model_state: 'ready' | 'missing' | 'dependency_missing' | 'error'
  model_path: string
  dataset_ready: boolean
  dataset_config: string
  device: string
  details?: string
}

export interface EvaluationJob {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  progress: number
  message: string
  created_at: string
  finished_at?: string
  metrics: Record<string, number>
}

export type ErrorType = 'TP' | 'FP' | 'FN' | 'MIXED'

export interface SampleAnalysis {
  attention_on_target: boolean | null
  background_interference: boolean | null
  missed_key_features: boolean | null
  causes: string[]
  conclusion: string
  improvement: string
}

export interface SampleRecord {
  id: string
  evaluation_id: string
  filename: string
  error_type: ErrorType
  gt_count: number
  prediction_count: number
  tp_count: number
  fp_count: number
  fn_count: number
  mean_confidence: number
  source_path: string
  image_url: string
  overlay_url: string
  cam_url?: string
  analysis: Partial<SampleAnalysis>
}

export interface Statistics {
  sample_count: number
  counts: Record<ErrorType, number>
  causes: Record<string, number>
  latest_evaluation: EvaluationJob | null
}

