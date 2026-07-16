<script setup lang="ts">
import { DatabaseZap } from '@lucide/vue'

withDefaults(defineProps<{ title: string; detail?: string }>(), { detail: '' })
</script>

<template>
  <div class="empty-state">
    <span class="empty-icon"><DatabaseZap :size="28" /></span>
    <strong>{{ title }}</strong>
    <p v-if="detail">{{ detail }}</p>
    <slot />
  </div>
</template>
