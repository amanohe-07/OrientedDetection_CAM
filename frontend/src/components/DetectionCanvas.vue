<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Detection } from '@/api/types'

const props = defineProps<{
  imageUrl: string
  imageWidth: number
  imageHeight: number
  detections: Detection[]
  selectedId?: string
  showLabels?: boolean
}>()
const emit = defineEmits<{ select: [id: string] }>()
const host = ref<HTMLDivElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const image = new Image()
let observer: ResizeObserver | null = null

const ratio = computed(() => `${props.imageWidth || 16} / ${props.imageHeight || 9}`)

function render() {
  if (!canvas.value || !host.value || !image.complete || !image.naturalWidth) return
  const bounds = host.value.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1
  canvas.value.width = Math.max(1, Math.round(bounds.width * dpr))
  canvas.value.height = Math.max(1, Math.round(bounds.height * dpr))
  const context = canvas.value.getContext('2d')
  if (!context) return
  context.scale(dpr, dpr)
  context.drawImage(image, 0, 0, bounds.width, bounds.height)
  const scaleX = bounds.width / props.imageWidth
  const scaleY = bounds.height / props.imageHeight
  props.detections.forEach((detection, index) => {
    const active = detection.id === props.selectedId
    const color = active ? '#ff00ff' : '#00ff88'
    context.beginPath()
    detection.box.polygon.forEach((point, pointIndex) => {
      const x = point.x * scaleX
      const y = point.y * scaleY
      if (pointIndex === 0) context.moveTo(x, y)
      else context.lineTo(x, y)
    })
    context.closePath()
    context.strokeStyle = color
    context.lineWidth = active ? 3 : 2
    context.shadowColor = 'rgba(0, 0, 0, .45)'
    context.shadowBlur = 2
    context.stroke()
    context.shadowBlur = 0
    if (props.showLabels !== false) {
      const anchor = detection.box.polygon[0]
      const label = `${index + 1}  ${detection.class_name} ${(detection.confidence * 100).toFixed(0)}%`
      context.font = '600 12px Consolas, "Microsoft YaHei UI", monospace'
      const labelWidth = context.measureText(label).width + 14
      const x = Math.max(0, Math.min(anchor.x * scaleX, bounds.width - labelWidth))
      const y = Math.max(22, anchor.y * scaleY)
      context.fillStyle = color
      context.fillRect(x, y - 21, labelWidth, 21)
      context.fillStyle = '#070a09'
      context.fillText(label, x + 7, y - 6)
    }
  })
}

function hitTest(event: MouseEvent) {
  if (!canvas.value) return
  const bounds = canvas.value.getBoundingClientRect()
  const x = ((event.clientX - bounds.left) / bounds.width) * props.imageWidth
  const y = ((event.clientY - bounds.top) / bounds.height) * props.imageHeight
  for (const detection of [...props.detections].reverse()) {
    if (pointInPolygon(x, y, detection.box.polygon)) {
      emit('select', detection.id)
      return
    }
  }
}

function pointInPolygon(x: number, y: number, polygon: Detection['box']['polygon']): boolean {
  let inside = false
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const current = polygon[i]
    const previous = polygon[j]
    const intersects =
      current.y > y !== previous.y > y &&
      x < ((previous.x - current.x) * (y - current.y)) / (previous.y - current.y) + current.x
    if (intersects) inside = !inside
  }
  return inside
}

function loadImage() {
  image.crossOrigin = 'anonymous'
  image.onload = () => nextTick(render)
  image.src = props.imageUrl
}

onMounted(() => {
  observer = new ResizeObserver(render)
  if (host.value) observer.observe(host.value)
  loadImage()
})
onBeforeUnmount(() => observer?.disconnect())
watch(() => props.imageUrl, loadImage)
watch(() => [props.detections, props.selectedId, props.showLabels], render, { deep: true })
</script>

<template>
  <div ref="host" class="detection-canvas" :style="{ aspectRatio: ratio }">
    <canvas ref="canvas" @click="hitTest" />
  </div>
</template>
