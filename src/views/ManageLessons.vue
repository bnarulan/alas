<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { BookOpen, CalendarPlus, Check, ClipboardList, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import EmptyState from '../components/EmptyState.vue'
import { dateInputAfter, dateLabel, subjectLabel } from '../format'
import { newId } from '../services/identifiers'
import { usePlatform } from '../stores/platform'
import type { Assignment, Lesson } from '../types'

const store = usePlatform()
const route = useRoute()
const confirm = ref<InstanceType<typeof ConfirmDialog>>()
const assignModal = ref<HTMLDialogElement>()
const activeLesson = ref<Lesson>()
const selectedClass = ref('')
const due = ref('')
const status = ref('')
const classAssignments = computed(() => activeLesson.value ? store.data.assignments.filter(item => item.lessonId === activeLesson.value!.id) : [])
function selectClass(id: string) {
  selectedClass.value = id
  due.value = classAssignments.value.find(item => item.classId === id)?.due ?? dateInputAfter(7)
}
async function openAssignment(lesson: Lesson) {
  activeLesson.value = lesson
  selectClass(store.data.classes[0]?.id ?? '')
  await nextTick()
  assignModal.value?.showModal()
}
function assign() {
  if (!activeLesson.value || !selectedClass.value || !due.value) return
  store.assign({ id: newId(), lessonId: activeLesson.value.id, classId: selectedClass.value, due: due.value })
  status.value = store.t('Сабақ сыныпқа тағайындалды.', 'Урок назначен классу.')
  assignModal.value?.close()
}
function removeLesson(lesson: Lesson) {
  confirm.value?.open(store.t('Сабақты жою', 'Удалить урок'),
    store.t('«' + lesson.title + '» сабағы, тапсырмалары және нәтижелері жойылады.', 'Урок «' + lesson.title + '», его задания и результаты будут удалены.'),
    () => { store.deleteLesson(lesson.id); status.value = store.t('Сабақ жойылды.', 'Урок удалён.') })
}
function removeAssignment(assignment: Assignment) {
  confirm.value?.open(store.t('Тапсырманы алып тастау', 'Снять задание'),
    store.t('Бұл сабақ сыныптың үй тапсырмалары тізімінен алынады.', 'Урок будет убран из домашних заданий класса.'),
    () => { store.removeAssignment(assignment.id); status.value = store.t('Тапсырма алынды.', 'Задание снято.') })
}
</script>

<template>
  <div class="page-stack">
    <header class="page-heading"><div><h1>{{ store.t('Сабақтарды басқару', 'Управление уроками') }}</h1><p>{{ store.t('Сабақтарды құрыңыз, жариялаңыз және сыныптарға тағайындаңыз.', 'Создавайте, публикуйте и назначайте уроки классам.') }}</p></div><RouterLink class="button primary" :to="{ name: 'editor' }"><Plus :size="18" />{{ store.t('Жаңа сабақ', 'Новый урок') }}</RouterLink></header>
    <p v-if="status || route.query.saved" class="status-box" role="status"><Check :size="18" />{{ status || store.t('Сабақ сақталды.', 'Урок сохранён.') }}</p>
    <section v-if="store.data.lessons.length" class="card panel management-list">
      <div class="section-title"><h2>{{ store.t('Сабақтар тізімі', 'Список уроков') }}</h2><span class="badge slate">{{ store.data.lessons.length }}</span></div>
      <article v-for="lesson in store.data.lessons" :key="lesson.id" class="management-row">
        <div class="management-main"><span class="icon-tile" :class="lesson.theme"><BookOpen :size="21" /></span><div><h3>{{ lesson.title }}</h3><p>{{ subjectLabel(lesson, store.locale) }} · {{ lesson.grade }} {{ store.t('сынып', 'класс') }} · {{ lesson.exercises.length }} {{ store.t('жаттығу', 'упр.') }}</p></div></div>
        <span class="badge" :class="lesson.published ? 'teal' : 'slate'">{{ lesson.published ? store.t('Жарияланған', 'Опубликован') : store.t('Нобай', 'Черновик') }}</span>
        <div class="row-actions"><button v-if="lesson.published" type="button" class="button secondary small" @click="openAssignment(lesson)"><CalendarPlus :size="16" />{{ store.t('Тағайындау', 'Назначить') }}</button><RouterLink class="icon-button" :aria-label="store.t('Өңдеу', 'Редактировать') + ' ' + lesson.title" :to="{ name: 'editor', params: { id: lesson.id } }"><Pencil :size="17" /></RouterLink><button class="icon-button remove-word" type="button" :aria-label="store.t('Жою', 'Удалить') + ' ' + lesson.title" @click="removeLesson(lesson)"><Trash2 :size="17" /></button></div>
      </article>
    </section>
    <div v-else class="card"><EmptyState :title="store.t('Сабақтар әзірге жоқ', 'Уроков пока нет')" /></div>
    <section class="card panel management-list">
      <div class="section-title"><h2><ClipboardList :size="20" />{{ store.t('Тағайындалған сабақтар', 'Назначенные уроки') }}</h2></div>
      <article v-for="assignment in store.data.assignments" :key="assignment.id" class="management-row">
        <div class="management-main"><span class="icon-tile blue"><ClipboardList :size="19" /></span><div><h3>{{ store.data.lessons.find(lesson => lesson.id === assignment.lessonId)?.title }}</h3><p>{{ store.data.classes.find(group => group.id === assignment.classId)?.name }} · {{ dateLabel(assignment.due, store.locale) }}</p></div></div>
        <div class="row-actions"><button type="button" class="icon-button remove-word" :aria-label="store.t('Тапсырманы алып тастау', 'Снять задание')" @click="removeAssignment(assignment)"><Trash2 :size="17" /></button></div>
      </article>
      <p v-if="!store.data.assignments.length" class="muted">{{ store.t('Сыныптарға сабақ әлі тағайындалмады.', 'Пока ни один урок не назначен классу.') }}</p>
    </section>
    <dialog ref="assignModal" class="modal" :aria-label="store.t('Сабақты тағайындау', 'Назначить урок')">
      <form class="modal-inner form-section" @submit.prevent="assign">
        <span class="icon-tile teal"><CalendarPlus :size="23" /></span><div><h2>{{ store.t('Сабақты тағайындау', 'Назначить урок') }}</h2><p>{{ activeLesson?.title }}</p></div>
        <template v-if="store.data.classes.length">
          <label class="field">{{ store.t('Сынып', 'Класс') }}<select autofocus :value="selectedClass" @change="selectClass(($event.target as HTMLSelectElement).value)"><option v-for="group in store.data.classes" :key="group.id" :value="group.id">{{ group.name }}</option></select></label>
          <label class="field">{{ store.t('Тапсыру мерзімі', 'Срок сдачи') }}<input v-model="due" type="date" required></label>
        </template>
        <p v-else class="muted">{{ store.t('Сабақ тағайындау үшін алдымен сынып құрыңыз.', 'Сначала создайте класс, чтобы назначить урок.') }} <RouterLink class="text-link" :to="{ name: 'classes' }" @click="assignModal?.close()">{{ store.t('Сыныптарға өту', 'К классам') }}</RouterLink></p>
        <div class="modal-actions"><button type="button" class="button secondary" @click="assignModal?.close()">{{ store.t('Болдырмау', 'Отмена') }}</button><button v-if="store.data.classes.length" class="button primary">{{ store.t('Тағайындау', 'Назначить') }}</button></div>
      </form>
    </dialog>
    <ConfirmDialog ref="confirm" />
  </div>
</template>
