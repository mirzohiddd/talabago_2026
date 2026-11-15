<script setup>
/**
 * Chatlar (talaba ↔ ish beruvchi). Har bir ish arizasi uchun bitta suhbat.
 * Desktop: chapda ro‘yxat, o‘ngda suhbat. Mobil: ro‘yxat yoki suhbat (/chats/:id).
 * Yangi xabarlar har 4 soniyada (ochiq suhbat) va 12 soniyada (ro‘yxat) olinadi — faqat sahifa ko‘rinib turganda.
 */
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Send, Check, CheckCheck, MessageCircle, Briefcase, Lock, Search } from 'lucide-vue-next'
import Avatar from '@/components/ui/Avatar.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import { chatApi } from '@/services'
import { session, toast } from '@/stores/session'
import { haptic } from '@/services/telegram'
import { t, date as fmtDate } from '@/i18n'

const route = useRoute()
const router = useRouter()
const base = computed(() => `/${route.meta.role}/chats`)
const chats = ref([])
const loading = ref(true)
const error = ref(null)
const q = ref('')
const activeId = computed(() => route.params.id || null)
const active = computed(() => chats.value.find((c) => c.id === activeId.value) || null)

async function loadChats(silent = false) {
  if (!silent) { loading.value = true; error.value = null }
  try { chats.value = await chatApi.list() } catch (e) { if (!silent) error.value = t(e.message) }
  loading.value = false
}
const shown = computed(() => {
  const s = q.value.trim().toLowerCase()
  return chats.value.filter((c) => !s || [c.other?.name, c.job?.title, c.job?.company].some((v) => v?.toLowerCase().includes(s)))
})

// ---------------- suhbat
const msgs = ref([])
const msgLoading = ref(false)
const text = ref('')
const sending = ref(false)
const box = ref(null)
const input = ref(null)
const me = computed(() => session.user?.id)
const lastAt = () => msgs.value.length ? msgs.value[msgs.value.length - 1].createdAt : undefined

async function scrollDown(smooth = false) {
  await nextTick()
  if (box.value) box.value.scrollTo({ top: box.value.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
}
async function openChat(id) {
  msgs.value = []
  if (!id) return
  msgLoading.value = true
  try {
    if (!chats.value.some((c) => c.id === id)) {          // to‘g‘ridan-to‘g‘ri havola (bildirishnoma) — ro‘yxatga qo‘shamiz
      const c = await chatApi.get(id)
      chats.value = [c, ...chats.value]
    }
    msgs.value = await chatApi.messages(id)
    markRead(id)
  } catch (e) { toast(t(e.message), 'error'); router.replace(base.value) }
  msgLoading.value = false
  scrollDown()
}
function markRead(id) {
  const c = chats.value.find((x) => x.id === id)
  if (c?.unread) { c.unread = 0; chatApi.read(id) }
}
async function poll() {
  if (document.visibilityState !== 'visible' || !activeId.value) return
  try {
    const fresh = await chatApi.messages(activeId.value, lastAt())
    const nearBottom = box.value && box.value.scrollHeight - box.value.scrollTop - box.value.clientHeight < 120
    const known = new Set(msgs.value.map((m) => m.id))
    const add = fresh.filter((m) => !known.has(m.id))
    if (add.length) {
      msgs.value.push(...add)
      if (add.some((m) => m.fromId !== me.value)) { chatApi.read(activeId.value); haptic.select() }
      if (nearBottom) scrollDown(true)
    }
    // o‘qilgan belgilarini yangilash (o‘zimiz yuborganlar)
    if (msgs.value.some((m) => m.fromId === me.value && !m.readAt)) {
      const all = await chatApi.messages(activeId.value)
      const byId = Object.fromEntries(all.map((m) => [m.id, m]))
      msgs.value = msgs.value.map((m) => byId[m.id] || m)
    }
  } catch { /* tarmoq uzilishi — keyingi urinishda */ }
}
async function send() {
  const v = text.value.trim()
  if (!v || sending.value || !activeId.value) return
  sending.value = true
  try {
    const m = await chatApi.send(activeId.value, v)
    msgs.value.push(m)
    text.value = ''
    const c = chats.value.find((x) => x.id === activeId.value)
    if (c) { c.lastMessage = { id: m.id, fromId: m.fromId, text: m.text, at: m.createdAt }; c.updatedAt = m.createdAt }
    chats.value = [...chats.value].sort((a, b) => (b.updatedAt || '').localeCompare(a.updatedAt || ''))
    haptic.tap()
    scrollDown(true)
    input.value?.focus()
  } catch (e) { toast(t(e.message), 'error') } finally { sending.value = false }
}
function onKey(e) { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send() } }

// sana ajratgichlari
const rows = computed(() => {
  const out = []; let day = ''
  for (const m of msgs.value) {
    const d = (m.createdAt || '').slice(0, 10)
    if (d !== day) { day = d; out.push({ sep: true, id: `d${d}`, label: fmtDate(m.createdAt) }) }
    out.push(m)
  }
  return out
})
const time = (iso) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
const preview = (c) => c.lastMessage ? `${c.lastMessage.fromId === me.value ? t('Siz') + ': ' : ''}${c.lastMessage.text}` : t('Hali xabar yo‘q — birinchi bo‘lib yozing')

let t1, t2
onMounted(async () => {
  await loadChats()
  if (activeId.value) openChat(activeId.value)
  t1 = setInterval(poll, 4000)
  t2 = setInterval(() => document.visibilityState === 'visible' && loadChats(true), 12000)
})
onBeforeUnmount(() => { clearInterval(t1); clearInterval(t2) })
watch(activeId, (id, old) => { if (id !== old) openChat(id) })
</script>

<template>
  <div class="page lg:pb-6!">
    <div class="lg:grid lg:grid-cols-[340px_1fr] lg:gap-4 lg:h-[calc(100dvh-140px)]">
      <!-- Ro‘yxat -->
      <section :class="['card overflow-hidden flex-col lg:flex', activeId ? 'hidden' : 'flex']" data-testid="chat-list">
        <div class="p-3 border-b border-line">
          <h1 class="text-[20px] font-extrabold px-1 mb-2">{{ $t('Chatlar') }}</h1>
          <label class="flex items-center gap-2 h-10 px-3 rounded-xl bg-surface"><Search class="size-4 text-muted" /><input v-model="q" type="search" class="flex-1 bg-transparent outline-none text-sm" :placeholder="$t('Ism yoki vakansiya...')" /></label>
        </div>
        <div class="flex-1 overflow-y-auto">
          <div v-if="loading" class="p-3"><SkeletonCard :count="3" /></div>
          <ErrorState v-else-if="error" :message="error" @retry="loadChats()" />
          <EmptyState v-else-if="!chats.length" :title="$t('Hali suhbat yo‘q')"
            :text="route.meta.role === 'student' ? $t('Vakansiyaga ariza yuborsangiz, ish beruvchi bilan chat shu yerda ochiladi.') : $t('Talaba ariza yuborgach, u bilan chat shu yerda ochiladi.')" illu="mail" />
          <button v-for="c in shown" :key="c.id" :class="['w-full flex items-start gap-3 p-3 text-left border-b border-line transition', c.id === activeId ? 'bg-brand-50' : 'hover:bg-surface']"
            :data-testid="`chat-${c.id}`" @click="router.push(`${base}/${c.id}`)">
            <Avatar :name="c.other?.name" size="sm" class="mt-0.5" />
            <span class="min-w-0 flex-1">
              <span class="flex items-center gap-2"><span class="font-bold truncate flex-1">{{ c.other?.name || '—' }}</span><span class="text-[11px] text-muted shrink-0">{{ c.lastMessage ? $ago(c.lastMessage.at) : '' }}</span></span>
              <span class="block text-[12px] text-brand-700 font-semibold truncate">{{ c.job?.title }}</span>
              <span class="flex items-center gap-2"><span :class="['block text-[13px] truncate flex-1', c.unread ? 'text-ink font-semibold' : 'text-muted']">{{ preview(c) }}</span>
                <span v-if="c.unread" class="min-w-[20px] h-5 px-1.5 rounded-full bg-brand text-white text-[11px] font-bold grid place-items-center" data-testid="chat-unread">{{ c.unread }}</span></span>
            </span>
          </button>
        </div>
      </section>

      <!-- Suhbat -->
      <section v-if="activeId" class="card overflow-hidden flex flex-col h-[calc(100dvh-170px)] lg:h-auto" data-testid="chat-room">
        <header class="flex items-center gap-3 p-3 border-b border-line">
          <button class="icon-btn lg:hidden" :aria-label="$t('Orqaga')" @click="router.push(base)"><ArrowLeft class="size-5" /></button>
          <Avatar :name="active?.other?.name" size="sm" />
          <div class="min-w-0 flex-1">
            <p class="font-bold truncate">{{ active?.other?.name || '…' }}</p>
            <p class="text-[12px] text-muted truncate flex items-center gap-1"><Briefcase class="size-3.5" />{{ active?.job?.title }}<template v-if="active?.job?.company"> · {{ active.job.company }}</template></p>
          </div>
          <StatusBadge v-if="active?.applicationStatus" :status="active.applicationStatus" class="hidden sm:inline-flex" />
        </header>
        <div ref="box" class="flex-1 overflow-y-auto p-4 space-y-2 bg-brand-25/40" aria-live="polite">
          <p v-if="msgLoading" class="text-center text-sm text-muted">{{ $t('Yuklanmoqda...') }}</p>
          <div v-else-if="!msgs.length" class="h-full grid place-items-center text-center px-6">
            <div><MessageCircle class="size-10 mx-auto text-brand-300" /><p class="mt-2 text-sm text-muted">{{ $t('Salom yozing — ariza bo‘yicha savollaringizni shu yerda muhokama qiling.') }}</p></div>
          </div>
          <template v-for="m in rows" :key="m.id">
            <p v-if="m.sep" class="text-center my-2"><span class="text-[11px] font-semibold text-muted bg-white border border-line rounded-full px-2.5 py-1">{{ m.label }}</span></p>
            <div v-else :class="['flex', m.fromId === me ? 'justify-end' : 'justify-start']">
              <div :class="['max-w-[82%] rounded-2xl px-3.5 py-2 text-[14.5px] leading-snug shadow-sm', m.fromId === me ? 'bg-brand text-white rounded-br-md' : 'bg-white border border-line rounded-bl-md', m.hidden && 'italic opacity-70']" data-testid="msg">
                <p class="whitespace-pre-wrap break-words">{{ m.text }}</p>
                <p :class="['text-[10.5px] mt-0.5 flex items-center gap-1 justify-end', m.fromId === me ? 'text-white/80' : 'text-muted']">
                  {{ time(m.createdAt) }}
                  <template v-if="m.fromId === me"><CheckCheck v-if="m.readAt" class="size-3.5" :aria-label="$t('O‘qildi')" data-testid="read-tick" /><Check v-else class="size-3.5" :aria-label="$t('Yuborildi')" /></template>
                </p>
              </div>
            </div>
          </template>
        </div>
        <footer class="p-3 border-t border-line bg-white">
          <p v-if="active?.locked" class="flex items-center gap-2 text-sm text-muted justify-center py-2"><Lock class="size-4" />{{ $t('Suhbat Support tomonidan cheklangan') }}</p>
          <p v-else-if="active?.other?.blocked" class="flex items-center gap-2 text-sm text-muted justify-center py-2"><Lock class="size-4" />{{ $t('Suhbatdosh bloklangan') }}</p>
          <form v-else class="flex items-end gap-2" @submit.prevent="send">
            <textarea ref="input" v-model="text" rows="1" maxlength="2000" :placeholder="$t('Xabar yozing...')" data-testid="chat-input"
              class="flex-1 resize-none max-h-32 min-h-[44px] rounded-xl bg-surface px-3.5 py-2.5 outline-none focus:ring-4 focus:ring-brand/10 focus:bg-white border border-transparent focus:border-brand text-[15px]"
              @keydown="onKey" />
            <button type="submit" :disabled="!text.trim() || sending" class="size-11 shrink-0 rounded-xl bg-brand text-white grid place-items-center disabled:opacity-40 hover:bg-brand-600 transition" :aria-label="$t('Yuborish')" data-testid="chat-send"><Send class="size-5" /></button>
          </form>
        </footer>
      </section>
      <section v-else class="hidden lg:grid card place-items-center text-center p-8">
        <div><MessageCircle class="size-12 mx-auto text-brand-300" /><p class="mt-3 font-bold">{{ $t('Suhbatni tanlang') }}</p><p class="text-sm text-muted">{{ $t('Chap tomondagi ro‘yxatdan suhbatni oching.') }}</p></div>
      </section>
    </div>
  </div>
</template>
