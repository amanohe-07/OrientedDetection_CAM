<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { BrainCircuit, RefreshCw, Save, Sparkles } from '@lucide/vue'
import { ElMessage } from 'element-plus'
import { api, apiError } from '@/api/client'
import type { ErrorType, EvaluationJob, SampleAnalysis, SampleRecord } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'

const jobs = ref<EvaluationJob[]>([])
const samples = ref<SampleRecord[]>([])
const selectedId = ref('')
const loading = ref(false)
const saving = ref(false)
const camLoading = ref(false)
const imageMode = ref<'original' | 'overlay' | 'cam'>('overlay')
const filters = reactive({ evaluation_id: '', error_type: '' as '' | ErrorType, search: '' })
const form = reactive<SampleAnalysis>({
  attention_on_target: null,
  background_interference: null,
  missed_key_features: null,
  causes: [],
  conclusion: '',
  improvement: '',
})

const causes = [
  '小目标或低分辨率', '密集目标抑制', '背景纹理干扰', '目标遮挡或截断',
  '旋转角度偏差', '长宽比异常', '域偏移', '标注问题', '阈值不合理',
]
const selected = computed(() => samples.value.find((item) => item.id === selectedId.value) ?? samples.value[0])
const currentImage = computed(() => {
  if (!selected.value) return ''
  if (imageMode.value === 'cam') return selected.value.cam_url ?? selected.value.overlay_url
  return imageMode.value === 'original' ? selected.value.image_url : selected.value.overlay_url
})

function errorType(type: ErrorType) {
  return type === 'TP' ? 'success' : type === 'FP' ? 'danger' : type === 'FN' ? 'warning' : 'info'
}

function hydrate(sample?: SampleRecord) {
  const analysis = sample?.analysis ?? {}
  form.attention_on_target = analysis.attention_on_target ?? null
  form.background_interference = analysis.background_interference ?? null
  form.missed_key_features = analysis.missed_key_features ?? null
  form.causes = [...(analysis.causes ?? [])]
  form.conclusion = analysis.conclusion ?? ''
  form.improvement = analysis.improvement ?? ''
}

async function load() {
  loading.value = true
  try {
    const params = {
      evaluation_id: filters.evaluation_id || undefined,
      error_type: filters.error_type || undefined,
      search: filters.search || undefined,
    }
    samples.value = await api.samples(params)
    if (!samples.value.some((item) => item.id === selectedId.value)) {
      selectedId.value = samples.value[0]?.id ?? ''
    }
    hydrate(selected.value)
  } catch (reason) {
    ElMessage.error(apiError(reason))
  } finally {
    loading.value = false
  }
}

async function generateCam() {
  if (!selected.value) return
  camLoading.value = true
  try {
    const updated = await api.generateCam(selected.value.id)
    const index = samples.value.findIndex((item) => item.id === updated.id)
    if (index >= 0) samples.value[index] = updated
    imageMode.value = 'cam'
    ElMessage.success('Eigen-CAM 已生成')
  } catch (reason) {
    ElMessage.error(apiError(reason))
  } finally {
    camLoading.value = false
  }
}

async function save() {
  if (!selected.value) return
  saving.value = true
  try {
    const updated = await api.saveAnalysis(selected.value.id, { ...form, causes: [...form.causes] })
    const index = samples.value.findIndex((item) => item.id === updated.id)
    if (index >= 0) samples.value[index] = updated
    ElMessage.success('归因分析已保存')
  } catch (reason) {
    ElMessage.error(apiError(reason))
  } finally {
    saving.value = false
  }
}

watch(selectedId, () => hydrate(selected.value))
watch(() => [filters.evaluation_id, filters.error_type], load)
onMounted(async () => {
  try { jobs.value = (await api.evaluations()).filter((item) => item.status === 'completed') } catch { jobs.value = [] }
  await load()
})
</script>

<template>
  <section>
    <div class="page-heading">
      <div><h2>错误样本归因</h2><p>预测、标注与模型关注区域联合分析</p></div>
      <el-button :icon="RefreshCw" :loading="loading" @click="load">刷新</el-button>
    </div>

    <div class="analysis-toolbar panel">
      <el-select v-model="filters.evaluation_id" clearable placeholder="全部评估任务">
        <el-option v-for="job in jobs" :key="job.id" :label="job.id" :value="job.id" />
      </el-select>
      <el-segmented v-model="filters.error_type" :options="[{ label: '全部', value: '' }, { label: 'FP', value: 'FP' }, { label: 'FN', value: 'FN' }, { label: 'TP', value: 'TP' }, { label: '混合', value: 'MIXED' }]" />
      <el-input v-model="filters.search" clearable placeholder="搜索文件名" @keyup.enter="load" />
    </div>

    <div v-if="samples.length" class="analysis-layout">
      <aside class="panel sample-browser">
        <div class="panel-header"><h3>样本队列</h3><small>{{ samples.length }}</small></div>
        <div class="sample-list">
          <button v-for="sample in samples" :key="sample.id" :class="{ active: sample.id === selected?.id }" @click="selectedId = sample.id">
            <img :src="sample.overlay_url" alt="" />
            <span><strong>{{ sample.filename }}</strong><small>GT {{ sample.gt_count }} · PRED {{ sample.prediction_count }}</small></span>
            <el-tag :type="errorType(sample.error_type)" effect="plain" size="small">{{ sample.error_type }}</el-tag>
          </button>
        </div>
      </aside>

      <div class="section-stack analysis-viewer">
        <article class="panel">
          <div class="panel-header">
            <h3>{{ selected?.filename }}</h3>
            <el-segmented v-model="imageMode" :options="[{ label: '原图', value: 'original' }, { label: '检测对比', value: 'overlay' }, { label: 'Eigen-CAM', value: 'cam' }]" />
          </div>
          <div class="sample-image"><img :src="currentImage" :alt="selected?.filename" /></div>
          <div class="visual-legend"><span class="gt"><i />GT / TP</span><span class="pred"><i />预测 TP</span><span class="fp"><i />FP</span><span class="fn"><i />FN</span></div>
          <el-button v-if="!selected?.cam_url" :icon="Sparkles" :loading="camLoading" class="cam-button" @click="generateCam">生成 Eigen-CAM</el-button>
        </article>
      </div>

      <aside class="panel attribution-form">
        <div class="panel-header"><h3>归因记录</h3><BrainCircuit :size="18" /></div>
        <label>关注目标区域</label>
        <el-segmented v-model="form.attention_on_target" :options="[{ label: '未知', value: null }, { label: '是', value: true }, { label: '否', value: false }]" block />
        <label>背景区域干扰</label>
        <el-segmented v-model="form.background_interference" :options="[{ label: '未知', value: null }, { label: '是', value: true }, { label: '否', value: false }]" block />
        <label>遗漏关键特征</label>
        <el-segmented v-model="form.missed_key_features" :options="[{ label: '未知', value: null }, { label: '是', value: true }, { label: '否', value: false }]" block />
        <label>可能原因</label>
        <el-checkbox-group v-model="form.causes" class="cause-checkboxes">
          <el-checkbox v-for="cause in causes" :key="cause" :value="cause">{{ cause }}</el-checkbox>
        </el-checkbox-group>
        <label>分析结论</label>
        <el-input v-model="form.conclusion" type="textarea" :rows="3" resize="none" />
        <label>改进方案</label>
        <el-input v-model="form.improvement" type="textarea" :rows="3" resize="none" />
        <el-button type="primary" :icon="Save" :loading="saving" class="save-button" @click="save">保存分析</el-button>
      </aside>
    </div>

    <EmptyState v-else title="暂无错误样本" detail="先在验证集评估页完成一次评估。" />
  </section>
</template>

<style scoped>
.analysis-toolbar { display: grid; grid-template-columns: minmax(180px, 260px) auto minmax(180px, 1fr); gap: 12px; margin-bottom: 16px; padding: 14px; }
.analysis-layout { display: grid; grid-template-columns: 270px minmax(400px, 1fr) 310px; align-items: start; gap: 16px; }
.sample-browser, .attribution-form { position: sticky; top: 104px; max-height: calc(100vh - 132px); overflow: hidden; }
.sample-list { display: grid; max-height: calc(100vh - 207px); overflow-y: auto; margin: 0 -8px; padding: 0 8px; }
.sample-list button { display: grid; grid-template-columns: 50px minmax(0, 1fr) auto; align-items: center; gap: 10px; min-height: 67px; padding: 8px; color: inherit; text-align: left; background: transparent; border: 1px solid transparent; border-bottom-color: var(--line); clip-path: var(--chamfer-sm); }
.sample-list button:hover, .sample-list button.active { color: var(--green); background: var(--green-soft); border-color: rgba(0, 255, 136, .4); }
.sample-list img { width: 50px; height: 46px; object-fit: cover; border: 1px solid #353547; }
.sample-list strong, .sample-list small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sample-list strong { font-size: 11px; }.sample-list small { margin-top: 5px; color: var(--muted); font-size: 9px; }
.sample-image { display: grid; min-height: 430px; max-height: calc(100vh - 285px); place-items: center; overflow: hidden; background: #050508; border: 1px solid #29293a; clip-path: var(--chamfer); }
.sample-image img { display: block; max-width: 100%; max-height: calc(100vh - 285px); object-fit: contain; }
.visual-legend { display: flex; flex-wrap: wrap; gap: 16px; margin-top: 12px; color: var(--muted); font-size: 10px; }
.visual-legend span { display: inline-flex; align-items: center; gap: 6px; }.visual-legend i { width: 14px; height: 3px; }
.visual-legend .gt i { background: var(--green); }.visual-legend .pred i { background: var(--blue); }.visual-legend .fp i { background: var(--red); }.visual-legend .fn i { background: var(--amber); }
.cam-button { margin-top: 14px; }
.attribution-form { overflow-y: auto; }
.attribution-form > label { display: block; margin: 18px 0 8px; color: var(--muted-strong); font-size: 11px; font-weight: 700; }
.attribution-form > label:first-of-type { margin-top: 0; }
.cause-checkboxes { display: grid; grid-template-columns: 1fr; gap: 3px; }
.cause-checkboxes :deep(.el-checkbox) { height: 26px; margin-right: 0; }
.save-button { width: 100%; min-height: 42px; margin-top: 20px; }
@media (max-width: 1280px) { .analysis-layout { grid-template-columns: 240px minmax(0, 1fr); } .attribution-form { position: static; grid-column: 1 / -1; max-height: none; } }
@media (max-width: 820px) { .analysis-toolbar { grid-template-columns: 1fr; } .analysis-layout { grid-template-columns: 1fr; } .sample-browser { position: static; max-height: 360px; } .sample-list { max-height: 290px; } .sample-image { min-height: 280px; } }
</style>
