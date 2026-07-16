<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { TooltipComponent } from 'echarts/components'
import { PieChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([TooltipComponent, PieChart, CanvasRenderer])

const props = defineProps<{ counts: Record<string, number> }>()
const host = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let observer: ResizeObserver | null = null

function render() {
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 个样本 · {d}%' },
    color: ['#00ff88', '#ff3366', '#ffb020', '#00d4ff'],
    series: [
      {
        type: 'pie',
        radius: ['60%', '82%'],
        center: ['50%', '50%'],
        silent: false,
        label: { show: false },
        itemStyle: { borderColor: '#12121a', borderWidth: 3, borderRadius: 0 },
        data: ['TP', 'FP', 'FN', 'MIXED'].map((name) => ({
          name,
          value: props.counts[name] ?? 0,
        })),
      },
    ],
  })
}

onMounted(() => {
  if (!host.value) return
  chart = echarts.init(host.value)
  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(host.value)
  render()
})
watch(() => props.counts, render, { deep: true })
onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
})
</script>

<template>
  <div ref="host" class="donut-chart" />
</template>
