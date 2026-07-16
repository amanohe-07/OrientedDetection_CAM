<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Activity, Crosshair, Database, Gauge, RefreshCw, Target, TriangleAlert } from '@lucide/vue'
import { api, apiError } from '@/api/client'
import type { Statistics } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'
import ErrorDonut from '@/components/ErrorDonut.vue'
import MetricTile from '@/components/MetricTile.vue'
import { useSystemStore } from '@/stores/system'

const system = useSystemStore()
const statistics = ref<Statistics | null>(null)
const loading = ref(false)
const error = ref('')

const metrics = computed(() => statistics.value?.latest_evaluation?.metrics ?? {})
const counts = computed(() => statistics.value?.counts ?? { TP: 0, FP: 0, FN: 0, MIXED: 0 })
const causeEntries = computed(() =>
  Object.entries(statistics.value?.causes ?? {}).sort((a, b) => b[1] - a[1]),
)

function percentage(value: unknown): string {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [data] = await Promise.all([api.statistics(), system.refresh()])
    statistics.value = data
  } catch (reason) {
    error.value = apiError(reason)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <div class="page-heading">
      <div>
        <h2>DOTA-v1.0 Ship 实验态势</h2>
        <p>模型、数据、评估与错误样本的当前状态</p>
      </div>
      <el-button :icon="RefreshCw" :loading="loading" @click="load">刷新</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="page-alert" />

    <div class="metric-grid">
      <MetricTile label="mAP@0.5" :value="percentage(metrics.map50)" note="旋转 IoU" tone="green" :icon="Target" />
      <MetricTile label="mAP@0.5:0.95" :value="percentage(metrics.map50_95)" note="官方 OBB 指标" tone="blue" :icon="Gauge" />
      <MetricTile label="假阳性 FP" :value="metrics.fp ?? 0" note="错误预测框" tone="red" :icon="TriangleAlert" />
      <MetricTile label="假阴性 FN" :value="metrics.fn ?? 0" note="遗漏真实目标" tone="amber" :icon="Crosshair" />
    </div>

    <div class="dashboard-grid">
      <article class="panel error-distribution">
        <div class="panel-header">
          <h3>样本构成</h3>
          <small>{{ statistics?.sample_count ?? 0 }} 个已索引样本</small>
        </div>
        <template v-if="statistics?.sample_count">
          <ErrorDonut :counts="counts" />
          <div class="chart-legend">
            <span><i class="tp" />TP {{ counts.TP }}</span>
            <span><i class="fp" />FP {{ counts.FP }}</span>
            <span><i class="fn" />FN {{ counts.FN }}</span>
            <span><i class="mixed" />混合 {{ counts.MIXED }}</span>
          </div>
        </template>
        <EmptyState v-else title="暂无评估记录" detail="完成一次验证集评估后生成样本构成。" />
      </article>

      <article class="panel">
        <div class="panel-header">
          <h3>运行条件</h3>
          <small>本机 CPU</small>
        </div>
        <div class="readiness-list">
          <div>
            <span class="readiness-icon"><Activity :size="18" /></span>
            <span><strong>后端 API</strong><small>FastAPI 服务</small></span>
            <b class="ok">可用</b>
          </div>
          <div>
            <span class="readiness-icon"><Target :size="18" /></span>
            <span><strong>模型权重</strong><small>{{ system.status?.model_path ?? 'weights/best.pt' }}</small></span>
            <b :class="system.status?.model_state === 'ready' ? 'ok' : 'pending'">
              {{ system.status?.model_state === 'ready' ? '可用' : '待配置' }}
            </b>
          </div>
          <div>
            <span class="readiness-icon"><Database :size="18" /></span>
            <span><strong>DOTA Ship</strong><small>{{ system.status?.dataset_config ?? 'datasets/dota_ship' }}</small></span>
            <b :class="system.status?.dataset_ready ? 'ok' : 'pending'">
              {{ system.status?.dataset_ready ? '可用' : '待配置' }}
            </b>
          </div>
        </div>
        <el-alert
          v-if="system.status?.details"
          :title="system.status.details"
          type="warning"
          :closable="false"
          show-icon
          class="status-alert"
        />
      </article>

      <article class="panel cause-panel">
        <div class="panel-header">
          <h3>错误归因排行</h3>
          <small>人工标注结果</small>
        </div>
        <div v-if="causeEntries.length" class="cause-list">
          <div v-for="([cause, count], index) in causeEntries" :key="cause">
            <span class="cause-rank">{{ String(index + 1).padStart(2, '0') }}</span>
            <strong>{{ cause }}</strong>
            <div class="cause-bar"><i :style="{ width: `${Math.max(8, (count / causeEntries[0][1]) * 100)}%` }" /></div>
            <b>{{ count }}</b>
          </div>
        </div>
        <EmptyState v-else title="暂无归因标签" detail="在错误归因页保存分析后显示统计。" />
      </article>
    </div>
  </section>
</template>

<style scoped>
.page-alert { margin-bottom: 16px; }
.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(340px, .9fr);
  gap: 16px;
  margin-top: 16px;
}
.cause-panel { grid-column: 1 / -1; }
.chart-legend { display: flex; justify-content: center; flex-wrap: wrap; gap: 17px; color: var(--muted); font-size: 11px; }
.chart-legend span { display: inline-flex; align-items: center; gap: 6px; }
.chart-legend i { width: 9px; height: 3px; box-shadow: 0 0 6px currentColor; }
.chart-legend .tp { color: var(--green); background: currentColor; }
.chart-legend .fp { color: var(--red); background: currentColor; }
.chart-legend .fn { color: var(--amber); background: currentColor; }
.chart-legend .mixed { color: var(--blue); background: currentColor; }
.readiness-list { display: grid; }
.readiness-list > div { display: grid; grid-template-columns: 38px minmax(0, 1fr) auto; align-items: center; gap: 11px; min-height: 66px; border-bottom: 1px solid var(--line); }
.readiness-list > div:last-child { border-bottom: 0; }
.readiness-icon { display: grid; width: 34px; height: 34px; place-items: center; color: var(--blue); background: rgba(0, 212, 255, .06); border: 1px solid rgba(0, 212, 255, .24); clip-path: var(--chamfer-sm); }
.readiness-list strong, .readiness-list small { display: block; }
.readiness-list strong { font-size: 13px; }
.readiness-list small { max-width: 360px; margin-top: 4px; overflow: hidden; color: var(--muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.readiness-list b { font-size: 11px; }
.readiness-list .ok { color: var(--green); }
.readiness-list .pending { color: var(--amber); }
.status-alert { margin-top: 14px; }
.cause-list { display: grid; }
.cause-list > div { display: grid; grid-template-columns: 34px minmax(140px, 220px) minmax(160px, 1fr) 28px; align-items: center; gap: 13px; min-height: 48px; border-bottom: 1px solid var(--line); }
.cause-list > div:last-child { border-bottom: 0; }
.cause-rank { color: var(--blue); font: 600 11px ui-monospace, monospace; }
.cause-list strong { font-size: 13px; }
.cause-bar { height: 4px; overflow: hidden; background: #292938; }
.cause-bar i { display: block; height: 100%; background: var(--green); box-shadow: 0 0 8px rgba(0, 255, 136, .45); }
.cause-list b { color: var(--muted-strong); font-size: 12px; }
@media (max-width: 980px) { .dashboard-grid { grid-template-columns: 1fr; } .cause-panel { grid-column: auto; } }
@media (max-width: 620px) { .cause-list > div { grid-template-columns: 28px minmax(100px, 1fr) 30px; } .cause-bar { display: none; } }
</style>
