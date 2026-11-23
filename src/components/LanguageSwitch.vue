<script setup lang="ts">
import { Globe2 } from 'lucide-vue-next'
import { usePlatform } from '../stores/platform'
const store = usePlatform()
</script>
<template>
  <div class="language-switch" role="group" :aria-label="store.t('Интерфейс тілі', 'Язык интерфейса')">
    <Globe2 :size="16" aria-hidden="true" />
    <button type="button" :aria-pressed="store.locale === 'kk'" :aria-label="store.t('Қазақша', 'Казахский')" @click="store.setLocale('kk')">KZ</button>
    <button type="button" :aria-pressed="store.locale === 'ru'" :aria-label="store.t('Орысша', 'Русский')" @click="store.setLocale('ru')">RU</button>
  </div>
</template>
