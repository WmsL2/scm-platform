<script setup lang="ts">
import { computed } from "vue"
import { formatOperationSeconds, type OperationTiming } from "./useOperationTimer"

const props = defineProps<{ timing: OperationTiming }>()
const description = computed(() => {
  if (props.timing.phase === "running") return "进行中，已耗时"
  if (props.timing.phase === "failed") return "失败，耗时"
  return "耗时"
})
</script>

<template>
  <p v-if="timing.phase !== 'idle'" class="operation-duration" role="status" aria-live="polite">
    {{ timing.label }}{{ description }} {{ formatOperationSeconds(timing.seconds) }}
  </p>
</template>

<style scoped>
.operation-duration { margin: 6px 0 0; color: var(--text-secondary, #606266); font-size: 12px; line-height: 1.5; }
</style>
