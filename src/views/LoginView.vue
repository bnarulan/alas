<script setup lang="ts">
import { BookOpen, GraduationCap, Presentation, ShieldCheck, Sparkles } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import BrandMark from '../components/BrandMark.vue'
import LanguageSwitch from '../components/LanguageSwitch.vue'
import { usePlatform } from '../stores/platform'
import type { Role } from '../types'

const store = usePlatform()
const router = useRouter()
function enter(role: Role) { store.signIn(role); void router.replace({ name: role }) }
</script>

<template>
  <div class="login-page">
    <header class="login-top"><BrandMark /><LanguageSwitch /></header>
    <main class="login-main">
      <section class="login-copy">
        <h1>{{ store.t('Қазақ тілін', 'Казахский язык') }}<br><em>{{ store.t('бірге үйренейік.', 'учим вместе.') }}</em></h1>
        <div class="login-roles">
          <button class="role-button role-primary" type="button" @click="enter('student')">
            <span class="role-icon"><GraduationCap :size="22" /></span><span><strong>{{ store.t('Оқушы ретінде кіру', 'Войти как ученик') }}</strong></span>
          </button>
          <button class="role-button" type="button" @click="enter('teacher')">
            <span class="role-icon"><Presentation :size="21" /></span><span><strong>{{ store.t('Мұғалім ретінде кіру', 'Войти как учитель') }}</strong></span>
          </button>
        </div>
      </section>
      <section class="login-visual" :aria-label="store.t('Кітап бетінен көтерілген қазақ даласының көрінісі', 'Казахская степь на страницах раскрытой книги')" role="img">
      </section>
    </main>
    <footer class="login-footer"><span>© {{ new Date().getFullYear() }} Alaś</span><span>{{ store.t('Қазақ тілін үйренуге арналған интерактивті орта', 'Интерактивная среда для изучения казахского языка') }}</span></footer>
  </div>
</template>
