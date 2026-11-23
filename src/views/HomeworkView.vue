<script setup lang="ts">
import { computed, ref } from 'vue'
import AssignmentList from '../components/AssignmentList.vue'
import { usePlatform } from '../stores/platform'
const store = usePlatform()
const filter = ref('all')
const assignments = computed(() => store.myAssignments.filter(assignment => {
  const lesson = store.catalog.find(item => item.id === assignment.lessonId)
  const done = lesson && store.lessonProgress(lesson) === 100
  return filter.value === 'all' || !!done === (filter.value === 'done')
}))
</script>
<template>
  <div class="page-stack">
    <header class="page-heading"><div><h1>{{ store.t('Үй тапсырмасы', 'Домашние задания') }}</h1><p>{{ store.t('Мұғалім тағайындаған сабақтар мен олардың мерзімі.', 'Уроки, назначенные учителем, и сроки сдачи.') }}</p></div></header>
    <div class="segments"><button v-for="[key, kk, ru] in [['all', 'Барлығы', 'Все'], ['todo', 'Орындалмаған', 'К выполнению'], ['done', 'Орындалған', 'Выполненные']]" :key="key" :aria-pressed="filter === key" @click="filter = key">{{ store.t(kk, ru) }}</button></div>
    <section class="card panel"><AssignmentList :assignments="assignments" /></section>
  </div>
</template>
