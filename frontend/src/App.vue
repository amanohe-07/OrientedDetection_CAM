<script setup lang="ts">
import { onMounted } from 'vue'
import AppShell from '@/components/AppShell.vue'
import { useSystemStore } from '@/stores/system'

const system = useSystemStore()
onMounted(() => system.refresh())
</script>

<template>
  <AppShell />
</template>

