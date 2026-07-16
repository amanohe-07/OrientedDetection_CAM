<script setup lang="ts">
import type { Component } from 'vue'

withDefaults(
  defineProps<{
    label: string
    value: string | number
    note?: string
    tone?: 'neutral' | 'green' | 'red' | 'amber' | 'blue'
    icon: Component
  }>(),
  { note: '', tone: 'neutral' },
)
</script>

<template>
  <article class="metric-tile" :class="`tone-${tone}`">
    <div class="metric-top">
      <span>{{ label }}</span>
      <span class="metric-icon"><component :is="icon" :size="18" /></span>
    </div>
    <strong>{{ value }}</strong>
    <small>{{ note || '—' }}</small>
  </article>
</template>

