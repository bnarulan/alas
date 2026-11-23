<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { TriangleAlert } from 'lucide-vue-next'
import { usePlatform } from '../stores/platform'

const store = usePlatform()
const dialog = ref<HTMLDialogElement>()
const title = ref('')
const description = ref('')
const action = ref<() => void>()
async function open(heading: string, detail: string, callback: () => void) {
  title.value = heading
  description.value = detail
  action.value = callback
  await nextTick()
  dialog.value?.showModal()
}
function confirm() { dialog.value?.close(); action.value?.() }
defineExpose({ open })
</script>

<template>
  <dialog ref="dialog" class="modal" :aria-label="title">
    <div class="modal-inner">
      <span class="icon-tile danger"><TriangleAlert :size="22" /></span>
      <h2>{{ title }}</h2><p>{{ description }}</p>
      <div class="modal-actions">
        <button autofocus class="button secondary" type="button" @click="dialog?.close()">{{ store.t('Болдырмау', 'Отмена') }}</button>
        <button class="button destructive" type="button" @click="confirm">{{ store.t('Растау', 'Подтвердить') }}</button>
      </div>
    </div>
  </dialog>
</template>
