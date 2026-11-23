<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { Pencil, Plus, Trash2, UsersRound } from 'lucide-vue-next'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import EmptyState from '../components/EmptyState.vue'
import { attemptsFor, averageScore } from '../services/analytics'
import { newId } from '../services/identifiers'
import { usePlatform } from '../stores/platform'
import type { Classroom } from '../types'

const store = usePlatform()
const dialog = ref<HTMLDialogElement>()
const confirm = ref<InstanceType<typeof ConfirmDialog>>()
const draft = ref<Classroom>()
const activeId = ref(store.data.classes[0]?.id)
const active = computed(() => store.data.classes.find(item => item.id === activeId.value))
const students = computed(() => store.data.users.filter(user => user.role === 'student'))
const members = computed(() => students.value.filter(user => active.value?.studentIds.includes(user.id)))
const assignedLessons = computed(() => store.catalog.filter(lesson => store.data.assignments.some(assignment => assignment.classId === activeId.value && assignment.lessonId === lesson.id)))
function progress(id: string) {
  return assignedLessons.value.length
    ? Math.round(assignedLessons.value.reduce((sum, lesson) => sum + store.lessonProgress(lesson, id), 0) / assignedLessons.value.length)
    : null
}
const classProgress = computed(() => {
  const values = members.value.map(member => progress(member.id)).filter((value): value is number => value !== null)
  return values.length ? Math.round(values.reduce((sum, item) => sum + item, 0) / values.length) : null
})
const score = (ids: string[]) => averageScore(attemptsFor(store.data.submissions, ids, assignedLessons.value.map(lesson => lesson.id)))
const percent = (value: number | null) => value === null ? '—' : value + '%'
async function edit(group?: Classroom) {
  draft.value = group ? { ...group, studentIds: [...group.studentIds] } : { id: newId(), name: '', grade: 9, studentIds: [] }
  await nextTick()
  dialog.value?.showModal()
}
function save() {
  if (!draft.value?.name) return
  store.saveClass({ ...draft.value, studentIds: [...draft.value.studentIds] })
  activeId.value = draft.value.id
  dialog.value?.close()
}
function remove(group: Classroom) {
  confirm.value?.open(store.t('Сыныпты жою', 'Удалить класс'),
    store.t(group.name + ' сыныбы және оған берілген тапсырмалар жойылады.', 'Класс ' + group.name + ' и его назначения будут удалены.'),
    () => {
      store.deleteClass(group.id)
      if (activeId.value === group.id) activeId.value = store.data.classes[0]?.id
    })
}
</script>

<template>
  <div class="page-stack">
    <header class="page-heading"><div><h1>{{ store.t('Сыныптар', 'Классы') }}</h1><p>{{ store.t('Сыныптарды, оқушыларды және тағайындалған сабақтардың барысын қараңыз.', 'Управляйте классами и отслеживайте прохождение назначенных уроков.') }}</p></div><button class="button primary" @click="edit()"><Plus :size="18" />{{ store.t('Сынып қосу', 'Добавить класс') }}</button></header>
    <div v-if="store.data.classes.length" class="class-grid">
      <div v-for="group in store.data.classes" :key="group.id" class="card class-card" :class="{ selected: activeId === group.id }">
        <button type="button" class="class-select" :aria-pressed="activeId === group.id" @click="activeId = group.id"><span class="icon-tile blue"><UsersRound :size="22" /></span><span><strong>{{ group.name }}</strong><small>{{ group.studentIds.length }} {{ store.t('оқушы', 'уч.') }} · {{ group.grade }} {{ store.t('сынып', 'класс') }}</small></span></button>
        <div class="row-actions"><button type="button" class="icon-button" :aria-label="store.t('Өңдеу', 'Редактировать') + ' ' + group.name" @click="edit(group)"><Pencil :size="17" /></button><button class="icon-button remove-word" type="button" :aria-label="store.t('Жою', 'Удалить') + ' ' + group.name" @click="remove(group)"><Trash2 :size="17" /></button></div>
      </div>
    </div>
    <div v-else class="card"><EmptyState :title="store.t('Сыныптар әзірге жоқ', 'Классов пока нет')" /></div>
    <section v-if="active" class="card panel class-detail">
      <div class="section-title"><h2>{{ active.name }} · {{ store.t('Оқушылар', 'Ученики') }}</h2><span class="badge teal">{{ assignedLessons.length }} {{ store.t('сабақ тағайындалды', 'уроков назначено') }}</span></div>
      <div class="class-analytics"><div><small>{{ store.t('Орташа ілгерілеу', 'Средний прогресс') }}</small><strong>{{ percent(classProgress) }}</strong></div><div><small>{{ store.t('Жауап дәлдігі', 'Точность ответов') }}</small><strong>{{ percent(score(active.studentIds)) }}</strong></div></div>
      <div v-if="members.length" class="table-wrap"><table><thead><tr><th scope="col">{{ store.t('Оқушы', 'Ученик') }}</th><th scope="col">{{ store.t('Тапсырма барысы', 'Прогресс заданий') }}</th><th scope="col">{{ store.t('Жауап дәлдігі', 'Точность ответов') }}</th><th scope="col">{{ store.t('Нәтижелер', 'Результаты') }}</th></tr></thead><tbody>
        <tr v-for="student in members" :key="student.id"><th scope="row"><span class="table-person"><span class="avatar">{{ student.initials }}</span>{{ store.locale === 'kk' ? student.name : student.nameRu }}</span></th><td><div class="table-progress"><progress v-if="progress(student.id) !== null" :value="progress(student.id) ?? 0" max="100" :aria-label="store.t('Тапсырма барысы', 'Прогресс заданий')"></progress>{{ percent(progress(student.id)) }}</div></td><td>{{ percent(score([student.id])) }}</td><td><RouterLink class="text-link" :to="{ name: 'results', query: { student: student.id, class: active.id } }">{{ store.t('Қарау', 'Открыть') }}</RouterLink></td></tr>
      </tbody></table></div>
      <EmptyState v-else :title="store.t('Сыныпта оқушы жоқ', 'В классе пока нет учеников')" :description="store.t('Сыныпты өңдеп, демо оқушыларды қосыңыз.', 'Откройте редактор класса, чтобы добавить демоучеников.')" />
    </section>
    <dialog ref="dialog" class="modal" :aria-label="store.t('Сыныпты басқару', 'Настройки класса')">
      <form v-if="draft" class="modal-inner form-section" @submit.prevent="save">
        <span class="icon-tile teal"><UsersRound :size="22" /></span><h2>{{ store.t('Сыныпты басқару', 'Настройки класса') }}</h2>
        <div class="form-grid"><label class="field">{{ store.t('Сынып атауы', 'Название класса') }}<input v-model.trim="draft.name" autofocus required maxlength="40"></label><label class="field">{{ store.t('Оқу сыныбы', 'Параллель') }}<input v-model.number="draft.grade" type="number" min="1" max="12" required></label></div>
        <fieldset class="member-options"><legend>{{ store.t('Оқушылар', 'Ученики') }}</legend><label v-for="student in students" :key="student.id"><input v-model="draft.studentIds" type="checkbox" :value="student.id">{{ store.locale === 'kk' ? student.name : student.nameRu }}</label></fieldset>
        <div class="modal-actions"><button type="button" class="button secondary" @click="dialog?.close()">{{ store.t('Болдырмау', 'Отмена') }}</button><button class="button primary">{{ store.t('Сақтау', 'Сохранить') }}</button></div>
      </form>
    </dialog>
    <ConfirmDialog ref="confirm" />
  </div>
</template>
