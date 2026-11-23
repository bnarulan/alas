<script setup lang="ts">
import { computed } from 'vue'
import { tokenize } from '../services/dictionary'

const props = defineProps<{ text: string; saved?: (word: string) => boolean }>()
const emit = defineEmits<{ word: [word: string, button: HTMLButtonElement] }>()
const tokens = computed(() => tokenize(props.text))
</script>

<template>
  <span lang="kk"><template v-for="(token, i) in tokens" :key="i"><button v-if="token.isWord" type="button" class="word-token" :class="{ 'word-saved': saved?.(token.value) }" aria-haspopup="dialog" @click.stop="emit('word', token.value, $event.currentTarget as HTMLButtonElement)">{{ token.value }}</button><span v-else>{{ token.value }}</span></template></span>
</template>
