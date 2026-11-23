<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'
defineProps<{ title: string; description?: string }>()
</script>
<template><div class="empty-state"><span class="icon-tile teal"><Inbox :size="24" /></span><h3>{{ title }}</h3><p v-if="description">{{ description }}</p><slot /></div></template>
