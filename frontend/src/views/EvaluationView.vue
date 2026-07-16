<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { Download, Play, RefreshCw, TestTube2 } from '@lucide/vue'
import { ElMessage } from 'element-plus'
import { api, apiError } from '@/api/client'
import type { EvaluationJob } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'
import MetricTile from '@/components/MetricTile.vue'
import { Activity, Crosshair, Gauge, Target } from '@lucide/vue'
import { useSystemStore } from '@/stores/system'

const system = useSystemStore()
const jobs = ref<EvaluationJob[]>([])
const selectedId = ref('')
const loading = ref(false)
const creating = ref(false)
const form = reactive({
  data_config: '',
  split: 'val',
  confidence: 0.25,
  match_iou: 0.5,
  image_size: 640,
})
let timer: number | undefined

const selected = computed(() => jobs.value.find((job) => job.id === selectedId.value) ?? jobs.value[0])
const activeJob = computed(() => jobs.value.find((job) => ['queued', 'running'].includes(job.status)))

function metricPercent(key: string): string {
  const value = selected.value?.metrics[key]
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—'
}

function statusLabel(status: EvaluationJob['status']) {
  return { queued: '排队中', running: '执行中', completed: '已完成', failed: '失败' }[status]
}

function statusType(status: EvaluationJob['status']) {
  return status === 'completed' ? 'success' : status === 'failed' ? 'danger' : status === 'running' ? 'primary' : 'info'
}

async function load(silent = false) {
  if (!silent) loading.value = true
  try {
    jobs.value = await api.evaluations()
    if (!selectedId.value && jobs.value.length) selectedId.value = jobs.value[0].id
  } catch (reason) {
    if (!silent) ElMessage.error(apiError(reason))
  } finally {
    loading.value = false
  }
}

async function createEvaluation() {
  creating.value = true
  try {
    const job = await api.createEvaluation({ ...form, data_config: form.data_config || undefined })
    jobs.value.unshift(job)
    selectedId.value = job.id
    ElMessage.success('评估任务已创建')
  } catch (reason) {
    ElMessage.error(apiError(reason))
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  await system.refresh()
  form.data_config = system.status?.dataset_config ?? ''
  await load()
  timer = window.setInterval(() => load(true), 2000)
})
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <section>
    <div class="page-heading">
      <div><h2>验证集评估</h2><p>旋转 IoU 匹配 · 官方 OBB mAP</p></div>
      <el-button :icon="RefreshCw" :loading="loading" @click="load()">刷新</el-button>
    </div>

    <div class="evaluation-layout">
      <aside class="panel evaluation-form">
        <div class="panel-header"><h3>新建评估</h3><TestTube2 :size="18" /></div>
        <el-form label-position="top">
          <el-form-item label="数据配置">
            <el-input v-model="form.data_config" placeholder="datasets/dota_ship/dota_ship.yaml" />
          </el-form-item>
          <el-form-item label="数据拆分">
            <el-segmented v-model="form.split" :options="[{ label: '训练集', value: 'train' }, { label: '验证集', value: 'val' }]" block />
          </el-form-item>
          <el-form-item label="置信度阈值">
            <div class="slider-row"><el-slider v-model="form.confidence" :min="0.01" :max="0.8" :step="0.01" /><b>{{ form.confidence.toFixed(2) }}</b></div>
          </el-form-item>
          <el-form-item label="匹配 IoU">
            <div class="slider-row"><el-slider v-model="form.match_iou" :min="0.1" :max="0.9" :step="0.05" /><b>{{ form.match_iou.toFixed(2) }}</b></div>
          </el-form-item>
          <el-form-item label="输入尺寸">
            <el-select v-model="form.image_size" style="width: 100%"><el-option :value="512" /><el-option :value="640" /><el-option :value="800" /></el-select>
          </el-form-item>
        </el-form>
        <el-button type="primary" :icon="Play" :loading="creating" :disabled="Boolean(activeJob)" class="create-button" @click="createEvaluation">
          {{ activeJob ? '已有任务执行中' : '开始评估' }}
        </el-button>
      </aside>

      <div class="section-stack evaluation-main">
        <div class="metric-grid evaluation-metrics">
          <MetricTile label="mAP@0.5" :value="metricPercent('map50')" note="旋转 IoU" tone="green" :icon="Target" />
          <MetricTile label="mAP@0.5:0.95" :value="metricPercent('map50_95')" note="COCO 范围" tone="blue" :icon="Gauge" />
          <MetricTile label="Precision" :value="metricPercent('precision')" note="TP / (TP + FP)" tone="neutral" :icon="Activity" />
          <MetricTile label="Recall" :value="metricPercent('recall')" note="TP / (TP + FN)" tone="amber" :icon="Crosshair" />
        </div>

        <article class="panel">
          <div class="panel-header">
            <h3>评估任务</h3>
            <a v-if="selected?.status === 'completed'" class="report-link" :href="`/api/reports/${selected.id}`" download><Download :size="15" />报告</a>
          </div>
          <el-table v-if="jobs.length" :data="jobs" highlight-current-row @current-change="(row: EvaluationJob) => selectedId = row?.id ?? ''">
            <el-table-column label="任务" min-width="130"><template #default="scope"><span class="job-id">{{ scope.row.id }}</span></template></el-table-column>
            <el-table-column label="状态" width="100"><template #default="scope"><el-tag :type="statusType(scope.row.status)" effect="plain">{{ statusLabel(scope.row.status) }}</el-tag></template></el-table-column>
            <el-table-column label="进度" min-width="190"><template #default="scope"><el-progress :percentage="scope.row.progress" :status="scope.row.status === 'failed' ? 'exception' : scope.row.status === 'completed' ? 'success' : undefined" /></template></el-table-column>
            <el-table-column prop="message" label="当前阶段" min-width="180" show-overflow-tooltip />
            <el-table-column label="样本" width="76"><template #default="scope">{{ scope.row.metrics.images ?? '—' }}</template></el-table-column>
          </el-table>
          <EmptyState v-else title="暂无评估任务" detail="配置 DOTA Ship 验证集后创建第一项评估。" />
        </article>

        <article v-if="selected" class="panel confusion-panel">
          <div class="panel-header"><h3>匹配统计</h3><small>IoU ≥ {{ form.match_iou.toFixed(2) }}</small></div>
          <div class="confusion-grid">
            <div class="tp"><span>TRUE POSITIVE</span><strong>{{ selected.metrics.tp ?? '—' }}</strong><small>正确检出</small></div>
            <div class="fp"><span>FALSE POSITIVE</span><strong>{{ selected.metrics.fp ?? '—' }}</strong><small>错误检出</small></div>
            <div class="fn"><span>FALSE NEGATIVE</span><strong>{{ selected.metrics.fn ?? '—' }}</strong><small>遗漏目标</small></div>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.evaluation-layout { display: grid; grid-template-columns: 300px minmax(0, 1fr); align-items: start; gap: 16px; }
.evaluation-form { position: sticky; top: 104px; }
.slider-row { display: grid; width: 100%; grid-template-columns: minmax(0, 1fr) 40px; align-items: center; gap: 12px; }
.slider-row b { color: var(--green); font: 600 12px ui-monospace, monospace; text-align: right; }
.create-button { width: 100%; min-height: 42px; }
.evaluation-metrics { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.evaluation-metrics :deep(.metric-tile) { min-height: 126px; }
.job-id { font: 600 11px ui-monospace, monospace; color: var(--blue); }
.report-link { display: inline-flex; min-height: 32px; align-items: center; gap: 6px; padding: 0 8px; color: var(--green); border: 1px solid rgba(0, 255, 136, .3); clip-path: var(--chamfer-sm); font-size: 11px; font-weight: 650; text-decoration: none; }
.report-link:hover { background: var(--green-soft); border-color: var(--green); box-shadow: var(--neon-green); }
.confusion-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.confusion-grid > div { min-height: 122px; padding: 18px; background: #0f0f17; border: 1px solid var(--line); border-left: 3px solid #727887; clip-path: var(--chamfer-sm); }
.confusion-grid .tp { border-left-color: var(--green); }.confusion-grid .fp { border-left-color: var(--red); }.confusion-grid .fn { border-left-color: var(--amber); }
.confusion-grid span, .confusion-grid small { display: block; color: var(--muted); font-size: 10px; font-weight: 650; }
.confusion-grid strong { display: block; margin: 10px 0 8px; font-size: 27px; }
.confusion-grid .tp strong { color: var(--green); }.confusion-grid .fp strong { color: var(--red); }.confusion-grid .fn strong { color: var(--amber); }
@media (max-width: 1080px) { .evaluation-layout { grid-template-columns: 1fr; } .evaluation-form { position: static; } .evaluation-metrics { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 560px) { .evaluation-metrics, .confusion-grid { grid-template-columns: 1fr; } }
</style>
