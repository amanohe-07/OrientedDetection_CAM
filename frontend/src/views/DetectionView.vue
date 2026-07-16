<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { Download, ImagePlus, ScanLine, SlidersHorizontal } from '@lucide/vue'
import type { UploadFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { api, apiError } from '@/api/client'
import type { Detection, InferenceResult } from '@/api/types'
import DetectionCanvas from '@/components/DetectionCanvas.vue'
import EmptyState from '@/components/EmptyState.vue'

const file = ref<File | null>(null)
const previewUrl = ref('')
const confidence = ref(0.25)
const iou = ref(0.45)
const imageSize = ref(640)
const loading = ref(false)
const result = ref<InferenceResult | null>(null)
const selectedId = ref('')
const showLabels = ref(true)

const selected = computed<Detection | null>(() =>
  result.value?.detections.find((item) => item.id === selectedId.value) ?? null,
)

function selectFile(upload: UploadFile) {
  if (!upload.raw) return
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  file.value = upload.raw
  previewUrl.value = URL.createObjectURL(upload.raw)
  result.value = null
  selectedId.value = ''
}

async function runInference() {
  if (!file.value) {
    ElMessage.warning('请先选择图像')
    return
  }
  loading.value = true
  try {
    result.value = await api.infer(file.value, confidence.value, iou.value, imageSize.value)
    selectedId.value = result.value.detections[0]?.id ?? ''
    ElMessage.success(`检测完成，共发现 ${result.value.detections.length} 个目标`)
  } catch (reason) {
    ElMessage.error(apiError(reason))
  } finally {
    loading.value = false
  }
}

function exportJson() {
  if (!result.value) return
  const blob = new Blob([JSON.stringify(result.value, null, 2)], { type: 'application/json' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `obb-detection-${result.value.id}.json`
  link.click()
  URL.revokeObjectURL(link.href)
}

onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<template>
  <section>
    <div class="page-heading">
      <div>
        <h2>单图旋转目标检测</h2>
        <p>YOLOv8n-OBB · CPU 推理</p>
      </div>
      <el-button v-if="result" :icon="Download" @click="exportJson">导出 JSON</el-button>
    </div>

    <div class="detect-layout">
      <aside class="panel controls-panel">
        <div class="panel-header"><h3>输入与参数</h3><SlidersHorizontal :size="18" /></div>
        <el-upload
          drag
          :auto-upload="false"
          :show-file-list="false"
          accept="image/jpeg,image/png,image/bmp,image/tiff"
          :on-change="selectFile"
          class="image-upload"
        >
          <ImagePlus :size="28" />
          <strong>{{ file?.name ?? '选择遥感图像' }}</strong>
          <small>JPG · PNG · BMP · TIFF</small>
        </el-upload>

        <div class="control-group">
          <div class="control-label"><span>置信度阈值</span><b>{{ confidence.toFixed(2) }}</b></div>
          <el-slider v-model="confidence" :min="0.01" :max="0.95" :step="0.01" />
        </div>
        <div class="control-group">
          <div class="control-label"><span>NMS IoU</span><b>{{ iou.toFixed(2) }}</b></div>
          <el-slider v-model="iou" :min="0.1" :max="0.9" :step="0.05" />
        </div>
        <div class="control-group">
          <span class="field-label">输入尺寸</span>
          <el-segmented v-model="imageSize" :options="[512, 640, 800]" block />
        </div>
        <el-button type="primary" :icon="ScanLine" :loading="loading" class="run-button" @click="runInference">
          执行检测
        </el-button>

        <div v-if="result" class="run-summary">
          <div><span>目标数量</span><strong>{{ result.detections.length }}</strong></div>
          <div><span>CPU 耗时</span><strong>{{ result.elapsed_ms.toFixed(0) }} ms</strong></div>
          <div><span>图像尺寸</span><strong>{{ result.image_width }} × {{ result.image_height }}</strong></div>
        </div>
      </aside>

      <div class="section-stack result-column">
        <article class="panel viewer-panel">
          <div class="panel-header">
            <h3>检测画布</h3>
            <el-switch v-if="result" v-model="showLabels" inline-prompt active-text="标签" inactive-text="标签" />
          </div>
          <DetectionCanvas
            v-if="result"
            :image-url="result.image_url"
            :image-width="result.image_width"
            :image-height="result.image_height"
            :detections="result.detections"
            :selected-id="selectedId"
            :show-labels="showLabels"
            @select="selectedId = $event"
          />
          <div v-else-if="previewUrl" class="preview-stage"><img :src="previewUrl" alt="待检测图像" /></div>
          <EmptyState v-else title="尚未选择图像" detail="选择一张 DOTA 船舶切片或同类遥感图像。" />
        </article>

        <article v-if="result" class="panel result-table-panel">
          <div class="panel-header"><h3>旋转框结果</h3><small>(cx, cy, w, h, angle)</small></div>
          <el-table :data="result.detections" max-height="320" highlight-current-row @current-change="(row: Detection) => selectedId = row?.id ?? ''">
            <el-table-column label="#" width="54">
              <template #default="scope">{{ scope.$index + 1 }}</template>
            </el-table-column>
            <el-table-column prop="class_name" label="类别" min-width="90" />
            <el-table-column label="置信度" width="95">
              <template #default="scope">{{ (scope.row.confidence * 100).toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column label="中心" min-width="150">
              <template #default="scope">{{ scope.row.box.cx.toFixed(1) }}, {{ scope.row.box.cy.toFixed(1) }}</template>
            </el-table-column>
            <el-table-column label="宽 × 高" min-width="145">
              <template #default="scope">{{ scope.row.box.width.toFixed(1) }} × {{ scope.row.box.height.toFixed(1) }}</template>
            </el-table-column>
            <el-table-column label="角度" width="90">
              <template #default="scope">{{ scope.row.box.angle_deg.toFixed(1) }}°</template>
            </el-table-column>
          </el-table>
        </article>
      </div>

      <aside v-if="selected" class="panel detail-panel">
        <div class="panel-header"><h3>目标详情</h3><span class="object-index">{{ selected.id }}</span></div>
        <div class="object-score"><span>SHIP</span><strong>{{ (selected.confidence * 100).toFixed(1) }}%</strong></div>
        <dl>
          <div><dt>中心 X</dt><dd>{{ selected.box.cx.toFixed(2) }}</dd></div>
          <div><dt>中心 Y</dt><dd>{{ selected.box.cy.toFixed(2) }}</dd></div>
          <div><dt>宽度</dt><dd>{{ selected.box.width.toFixed(2) }}</dd></div>
          <div><dt>高度</dt><dd>{{ selected.box.height.toFixed(2) }}</dd></div>
          <div><dt>角度</dt><dd>{{ selected.box.angle_deg.toFixed(2) }}°</dd></div>
        </dl>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.detect-layout { display: grid; grid-template-columns: 286px minmax(420px, 1fr) 0; gap: 16px; align-items: start; transition: grid-template-columns 180ms ease; }
.detect-layout:has(.detail-panel) { grid-template-columns: 286px minmax(420px, 1fr) 220px; }
.controls-panel, .detail-panel { position: sticky; top: 104px; }
.image-upload :deep(.el-upload) { width: 100%; }
.image-upload :deep(.el-upload-dragger) { display: grid; width: 100%; min-height: 148px; place-items: center; align-content: center; gap: 7px; padding: 18px; color: var(--blue); background: #0d0d14; border-color: #363649; clip-path: var(--chamfer); }
.image-upload :deep(.el-upload-dragger:hover) { color: var(--green); border-color: var(--green); box-shadow: inset 0 0 20px rgba(0, 255, 136, .04), var(--neon-green); }
.image-upload strong, .image-upload small { display: block; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.image-upload small { color: var(--muted); font-size: 10px; }
.control-group { margin-top: 22px; }
.control-label { display: flex; justify-content: space-between; color: var(--muted-strong); font-size: 11px; font-weight: 600; }
.control-label b { color: var(--green); font-family: ui-monospace, monospace; }
.run-button { width: 100%; min-height: 42px; margin-top: 24px; }
.run-summary { display: grid; gap: 0; margin-top: 20px; border-top: 1px solid var(--line); }
.run-summary > div { display: flex; justify-content: space-between; gap: 10px; padding: 12px 0; border-bottom: 1px solid var(--line); font-size: 11px; }
.run-summary span { color: var(--muted); }
.run-summary strong { color: var(--blue); font-variant-numeric: tabular-nums; }
.viewer-panel { min-width: 0; }
.preview-stage { display: grid; min-height: 360px; max-height: calc(100vh - 230px); place-items: center; overflow: hidden; background: #050508; border: 1px solid #29293a; clip-path: var(--chamfer); }
.preview-stage img { display: block; max-width: 100%; max-height: calc(100vh - 230px); object-fit: contain; }
.result-table-panel { min-width: 0; }
.detail-panel { overflow: hidden; }
.object-index { max-width: 110px; overflow: hidden; color: var(--muted); font: 600 10px ui-monospace, monospace; text-overflow: ellipsis; white-space: nowrap; }
.object-score { padding: 16px; background: rgba(0, 255, 136, .07); border-left: 3px solid var(--green); }
.object-score span, .object-score strong { display: block; }
.object-score span { color: var(--muted-strong); font-size: 10px; font-weight: 750; }
.object-score strong { margin-top: 5px; color: var(--green); font-size: 25px; text-shadow: 0 0 12px rgba(0, 255, 136, .25); }
dl { margin: 17px 0 0; }
dl div { display: flex; justify-content: space-between; min-height: 38px; align-items: center; border-bottom: 1px solid var(--line); font-size: 11px; }
dt { color: var(--muted); } dd { margin: 0; color: var(--blue); font-family: ui-monospace, monospace; font-weight: 650; }
@media (max-width: 1320px) { .detect-layout, .detect-layout:has(.detail-panel) { grid-template-columns: 270px minmax(0, 1fr); } .detail-panel { display: none; } }
@media (max-width: 820px) { .detect-layout, .detect-layout:has(.detail-panel) { grid-template-columns: 1fr; } .controls-panel { position: static; } }
</style>
