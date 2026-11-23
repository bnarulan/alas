<script setup lang="ts">
import { Settings2 } from 'lucide-vue-next'
import { pronunciationPreferences, speechSpeeds } from '../services/pronunciation'
import { usePlatform } from '../stores/platform'

const store = usePlatform()
const speeds = [
  ['Баяу', 'Медленно'], ['Үйренуге', 'Для обучения'],
  ['Қалыпты', 'Обычно'], ['Жылдам', 'Быстро'],
]
</script>

<template>
  <details class="pronunciation-settings">
    <summary><Settings2 :size="16" />{{ store.t('Дыбыстау баптаулары', 'Настройки озвучивания') }}</summary>
    <div class="pronunciation-options">
      <label class="field">{{ store.t('Дыбыстау дауысы', 'Голос озвучивания') }}
        <select v-model="pronunciationPreferences.voice">
          <option value="female">{{ store.t('Әйел дауысы', 'Женский голос') }}</option>
          <option value="male">{{ store.t('Ер дауысы', 'Мужской голос') }}</option>
        </select>
      </label>
      <label class="field">{{ store.t('Оқу жылдамдығы', 'Скорость чтения') }}
        <select v-model="pronunciationPreferences.speed">
          <option v-for="(speed, i) in speechSpeeds" :key="speed" :value="speed">{{ store.t(speeds[i][0], speeds[i][1]) }} · {{ speed }}×</option>
        </select>
      </label>
    </div>
  </details>
</template>
