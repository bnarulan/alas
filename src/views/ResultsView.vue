<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { CircleCheck, CircleX, ListChecks } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import EmptyState from '../components/EmptyState.vue'
import { dateLabel } from '../format'
import { averageScore } from '../services/analytics'
import { usePlatform } from '../stores/platform'
import type { Submission } from '../types'

const store = usePlatform()
const route = useRoute()
const selectedStudent = ref(typeof route.query.student === 'string' ? route.query.student : '')
const selectedClass = ref(typeof route.query.class === 'string' ? route.query.class : '')
const selectedLesson = ref('')
const detail = ref<Submission>()
const modal = ref<HTMLDialogElement>()
const classGroup = computed(() => store.data.classes.find(group => group.id === selectedClass.value))
const students = computed(() => store.data.users.filter(user => user.role === 'student' && (!classGroup.value || classGroup.value.studentIds.includes(user.id))))
const results = computed(() => store.data.submissions.filter(item =>
  (!classGroup.value || classGroup.value.studentIds.includes(item.userId))
    && (!selectedStudent.value || selectedStudent.value === item.userId)
    && (!selectedLesson.value || selectedLesson.value === item.lessonId)).sort((a, b) => b.createdAt - a.createdAt))
const accuracy = computed(() => averageScore(results.value))
function studentName(id: string) {
  const student = store.data.users.find(user => user.id === id)
  return store.locale === 'kk' ? student?.name : student?.nameRu
}
function lessonName(id: string) { return store.data.lessons.find(lesson => lesson.id === id)?.title }
async function review(result: Submission) { detail.value = result; await nextTick(); modal.value?.showModal() }
</script>

<template>
  <div class="page-stack">
    <header class="page-heading"><div><h1>{{ store.t('Нәтижелер', 'Результаты') }}</h1><p>{{ store.t('Оқушылардың жауаптарын қарап, жаттығу нәтижелерін талдаңыз.', 'Просматривайте ответы учеников и анализируйте результаты упражнений.') }}</p></div></header>
    <section class="card panel form-section">
      <div class="form-grid cols-three"><label class="field">{{ store.t('Сынып', 'Класс') }}<select v-model="selectedClass" @change="selectedStudent = ''"><option value="">{{ store.t('Барлық сынып', 'Все классы') }}</option><option v-for="group in store.data.classes" :key="group.id" :value="group.id">{{ group.name }}</option></select></label><label class="field">{{ store.t('Оқушы', 'Ученик') }}<select v-model="selectedStudent"><option value="">{{ store.t('Барлық оқушы', 'Все ученики') }}</option><option v-for="student in students" :key="student.id" :value="student.id">{{ store.locale === 'kk' ? student.name : student.nameRu }}</option></select></label><label class="field">{{ store.t('Сабақ', 'Урок') }}<select v-model="selectedLesson"><option value="">{{ store.t('Барлық сабақ', 'Все уроки') }}</option><option v-for="lesson in store.data.lessons" :key="lesson.id" :value="lesson.id">{{ lesson.title }}</option></select></label></div>
      <div class="class-analytics"><div><small>{{ store.t('Жіберілген жауаптар', 'Отправленные попытки') }}</small><strong>{{ results.length }}</strong></div><div><small>{{ store.t('Соңғы жауаптардың дәлдігі', 'Точность последних ответов') }}</small><strong>{{ accuracy === null ? '—' : accuracy + '%' }}</strong></div></div>
    </section>
    <section class="card panel">
      <div class="section-title"><h2>{{ store.t('Жаттығу жауаптары', 'Ответы на упражнения') }}</h2></div>
      <div v-if="results.length" class="table-wrap"><table><thead><tr><th scope="col">{{ store.t('Оқушы', 'Ученик') }}</th><th scope="col">{{ store.t('Сабақ пен жаттығу', 'Урок и упражнение') }}</th><th scope="col">{{ store.t('Ұпай', 'Баллы') }}</th><th scope="col">{{ store.t('Күні', 'Дата') }}</th><th scope="col">{{ store.t('Шолу', 'Проверка') }}</th></tr></thead><tbody>
        <tr v-for="result in results" :key="result.id"><th scope="row">{{ studentName(result.userId) }}</th><td><strong>{{ lessonName(result.lessonId) }}</strong><small>{{ result.prompt }}</small></td><td><span class="badge" :class="result.score === result.possible ? 'teal' : 'orange'">{{ result.score }} / {{ result.possible }}</span></td><td>{{ dateLabel(result.createdAt, store.locale) }}</td><td><button type="button" class="button secondary small" @click="review(result)">{{ store.t('Жауаптарды қарау', 'Посмотреть ответы') }}</button></td></tr>
      </tbody></table></div>
      <EmptyState v-else :title="store.t('Жауаптар әзірге жоқ', 'Пока ответов нет')" :description="store.t('Оқушы жаттығуды тапсырғаннан кейін нәтижесі осында шығады.', 'Результат появится здесь после отправки упражнения.')"/>
    </section>
    <dialog ref="modal" class="modal result-modal" :aria-label="store.t('Жаттығу нәтижесі', 'Результат упражнения')">
      <div v-if="detail" class="modal-inner form-section"><span class="icon-tile teal"><ListChecks :size="22" /></span><div><h2>{{ store.t('Жаттығу нәтижесі', 'Результат упражнения') }} · {{ detail.score }} / {{ detail.possible }}</h2><p>{{ studentName(detail.userId) }} · {{ lessonName(detail.lessonId) }}</p></div>
        <div v-for="(line, index) in detail.lines" :key="index" class="answer-line"><span class="answer-mark" :class="{ good: line.correct }"><component :is="line.correct ? CircleCheck : CircleX" :size="17" /></span><div><strong>{{ line.prompt }}</strong><p>{{ store.t('Оқушы жауабы', 'Ответ ученика') }} · {{ line.answer }}</p><p>{{ store.t('Дұрыс жауап', 'Правильный ответ') }} · <b>{{ line.expected }}</b></p></div></div>
        <div class="modal-actions"><button type="button" autofocus class="button secondary" @click="modal?.close()">{{ store.t('Жабу', 'Закрыть') }}</button></div>
      </div>
    </dialog>
  </div>
</template>
