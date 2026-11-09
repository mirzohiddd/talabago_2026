<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { CheckCircle2, Briefcase, Home, Inbox, Eye, User, BellOff, CalendarClock, LifeBuoy, XCircle, Clock } from 'lucide-vue-next'
import PopoverPanel from './PopoverPanel.vue'
import { notificationsApi } from '@/services'
import { session } from '@/stores/session'

const open = defineModel({ type: Boolean })
const emit = defineEmits(['count'])
const router = useRouter()
const items = ref([])
const loading = ref(true)
const icons = { check: CheckCircle2, briefcase: Briefcase, home: Home, inbox: Inbox, eye: Eye, user: User, calendar: CalendarClock, life: LifeBuoy, x: XCircle, clock: Clock }

async function load(quiet = false) {
  if (!session.token) return
  if (!quiet) loading.value = true
  try {
    items.value = await notificationsApi.list()
    emit('count', items.value.filter((n) => !n.read).length)
  } catch { /* tarmoq xatosi — keyingi urinishda */ } finally {
    loading.value = false
  }
}
// Yangi bildirishnomalar: har 45 soniyada (sahifa ko‘rinib turganda) yangilanadi
const timer = setInterval(() => { if (document.visibilityState === 'visible') load(true) }, 45000)
onBeforeUnmount(() => clearInterval(timer))
async function readAll() {
  await notificationsApi.readAll()
  items.value.forEach((n) => (n.read = true))
  emit('count', 0)
}
function go(n) { open.value = false; if (n.link) router.push(n.link) }
watch(() => session.userId, () => load(), { immediate: true })
watch(open, (v) => v && load())
</script>

<template>
  <PopoverPanel v-model="open" :title="$t('Bildirishnomalar')">
    <template #action>
      <button v-if="items.some((n) => !n.read)" class="text-[13px] font-semibold text-brand-600 hover:underline" @click="readAll">{{ $t('Hammasini o‘qilgan qilish') }}</button>
    </template>
    <div class="max-h-[60vh] overflow-y-auto pb-2" data-testid="notifications">
      <div v-if="loading" class="p-4 space-y-3">
        <div v-for="i in 3" :key="i" class="flex gap-3"><div class="skeleton size-10" /><div class="flex-1 space-y-2"><div class="skeleton h-3.5 w-2/3" /><div class="skeleton h-3 w-full" /></div></div>
      </div>
      <div v-else-if="!items.length" class="py-10 text-center text-muted text-sm">
        <BellOff class="size-8 mx-auto mb-2 text-line" />{{ $t('Hozircha bildirishnoma yo‘q') }}
      </div>
      <div v-else class="stagger">
        <button v-for="n in items" :key="n.id" :class="['w-full text-left flex gap-3 px-4 py-3 transition-colors hover:bg-surface', !n.read && 'bg-brand-50/60']" @click="go(n)">
          <span :class="['size-10 rounded-xl grid place-items-center shrink-0', n.read ? 'bg-surface text-ink-2' : 'bg-brand text-white']">
            <component :is="icons[n.icon] || Inbox" class="size-[18px]" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="font-semibold text-sm flex items-center gap-2">{{ $t(n.title) }}<span v-if="!n.read" class="size-2 rounded-full bg-brand" /></span>
            <span class="block text-[13px] text-ink-2 leading-snug">{{ $tc(n.text) }}</span>
            <span class="block text-xs text-muted mt-1">{{ $ago(n.createdAt) }}</span>
          </span>
        </button>
      </div>
    </div>
  </PopoverPanel>
</template>
