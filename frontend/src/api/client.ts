import axios from 'axios'
import type {
  EvaluationJob,
  InferenceResult,
  SampleAnalysis,
  SampleRecord,
  Statistics,
  SystemStatus,
} from './types'

const client = axios.create({ baseURL: '/api', timeout: 120_000 })

export function apiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    return typeof detail === 'string' ? detail : error.message
  }
  return error instanceof Error ? error.message : '请求失败'
}

export const api = {
  system: async () => (await client.get<SystemStatus>('/system')).data,
  statistics: async () => (await client.get<Statistics>('/statistics')).data,
  infer: async (file: File, confidence: number, iou: number, imageSize: number) => {
    const body = new FormData()
    body.append('image', file)
    body.append('confidence', String(confidence))
    body.append('iou', String(iou))
    body.append('image_size', String(imageSize))
    return (await client.post<InferenceResult>('/inference', body)).data
  },
  evaluations: async () => (await client.get<EvaluationJob[]>('/evaluations')).data,
  evaluation: async (id: string) => (await client.get<EvaluationJob>(`/evaluations/${id}`)).data,
  createEvaluation: async (payload: {
    data_config?: string
    split: string
    confidence: number
    match_iou: number
    image_size: number
  }) => (await client.post<EvaluationJob>('/evaluations', payload)).data,
  samples: async (params?: { evaluation_id?: string; error_type?: string; search?: string }) =>
    (await client.get<SampleRecord[]>('/samples', { params })).data,
  saveAnalysis: async (id: string, payload: SampleAnalysis) =>
    (await client.put<SampleRecord>(`/samples/${id}/analysis`, payload)).data,
  generateCam: async (id: string, layerIndex = -2, opacity = 0.48) =>
    (await client.post<SampleRecord>(`/samples/${id}/cam`, {
      layer_index: layerIndex,
      opacity,
    })).data,
}

