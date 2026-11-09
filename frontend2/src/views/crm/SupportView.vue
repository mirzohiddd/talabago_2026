<script setup>
/**
 * Support inbox: chapda murojaatlar, markazda chat, o‘ngda foydalanuvchi (desktop).
 * Mobil: ro‘yxat → chat; foydalanuvchi ma’lumoti alohida panelda.
 * Kelajak: javob saqlangach backend Telegram bot orqali foydalanuvchiga xabar yuboradi (notify_user).
 */
import { ref, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, SendHorizontal, CheckCircle2, RotateCcw, UserRound, Phone, Send, Paperclip, Info, LifeBuoy, MessageSquareText } from 'lucide-vue-next'
import SearchBox from '@/components/crm/SearchBox.vue'
import SideDrawer from '@/components/crm/SideDrawer.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import Avatar from '@/components/ui/Avatar.vue'
import MediaImg from '@/components/ui/MediaImg.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import { crmStore, ensureCrmLoaded, crmApi, fullName } from '@/services/crm'
import { TICKET_TYPES, TICKET_STATUSES, STATUS, ROLE_LABELS } from '@/config/status'
import { resolveMedia } from '@/composables/useMediaUrl'
import { toast } from '@/stores/toast'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()
const loading = ref(!crmStore.loaded)
ensureCrmLoaded().then(() => (loading.value = false))

const status = ref('open')
const type = ref('all')
const q = ref('')
const chips = computed(() => [
  { value: 'open', label: `${t('Ochiq')} · ${crmStore.tickets.filter((x) => x.status !== 'resolved').length}` },
  ...TICKET_STATUSES.map((s) => ({ value: s, label: `${t(STATUS[s].label)} · ${crmStore.tickets.filter((x) => x.status === s).length}` })),
  { value: 'all', label: t('Barchasi') },
])
const typeOpts = computed(() => [{ value: 'all', label: t('Barcha turlar') }, ...TICKET_TYPES.map((x) => ({ value: x.value, label: t(x.label) }))])
const typeLabel = (v) => t(TICKET_TYPES.find((x) => x.value === v)?.label || v)
const user = (id) => crmStore.users.find((u) => u.id === id)
const list = computed(() => {
  const s = q.value.trim().toLowerCase()
  return crmStore.tickets
    .filter((x) => status.value === 'all' || (status.value === 'open' ? x.status !== 'resolved' : x.status === status.value))
    .filter((x) => type.value === 'all' || x.type === type.value)
    .filter((x) => !s || [x.subject, fullName(user(x.userId)), user(x.userId)?.phone, ...x.messages.map((m) => m.text)].some((v) => v?.toLowerCase().includes(s)))
    .sort((a, b) => (b.unreadBySupport ? 1 : 0) - (a.unreadBySupport ? 1 : 0) || Date.parse(b.updatedAt) - Date.parse(a.updatedAt))
})

const activeId = computed(() => route.params.id || null)
const ticket = computed(() => crmStore.tickets.find((x) => x.id === activeId.value) || null)
const owner = computed(() => ticket.value && user(ticket.value.userId))
const scroller = ref(null)
watch([ticket, () => ticket.value?.messages.length], async () => {
  if (ticket.value?.unreadBySupport) { ticket.value.unreadBySupport = 0 }
  if (ticket.value?.status === 'new') await crmApi.setTicketStatus(ticket.value.id, 'in_review')
  await nextTick(); if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}, { immediate: true })

const draft = ref('')
const nextStatus = ref('answered')
const sending = ref(false)
const QUICK = ['Assalomu alaykum! Murojaatingiz uchun rahmat.', 'Muammoni tekshiryapmiz, tez orada javob beramiz.', 'Iltimos, muammo skrinshotini yuboring.', 'Muammo hal qilindi. Yana savol bo‘lsa, yozing.']
async function send() {
  if (!draft.value.trim()) return
  sending.value = true
  await crmApi.replyTicket(ticket.value.id, draft.value.trim(), { status: nextStatus.value })
  draft.value = ''
  sending.value = false
  toast(t('Javob yuborildi'))
}
async function close() { await crmApi.setTicketStatus(ticket.value.id, 'resolved'); toast(t('Murojaat yopildi')) }
async function reopen() { await crmApi.setTicketStatus(ticket.value.id, 'in_review'); toast(t('Murojaat qayta ochildi')) }
const infoOpen = ref(false)
const related = computed(() => crmStore.tickets.filter((x) => x.userId === ticket.value?.userId && x.id !== ticket.value?.id))
async function openAtt(a) { const u = await resolveMedia(a.url); if (u) window.open(u, '_blank', 'noopener') }
function onEnter(e) { if (e.ctrlKey || e.metaKey) send() }
</script>

<template>
  <div class="grid lg:grid-cols-[340px_minmax(0,1fr)] xl:grid-cols-[340px_minmax(0,1fr)_300px] gap-4 h-[calc(100dvh-64px-72px)] min-h-[520px]" data-testid="support-inbox">
    <!-- Ro‘yxat -->
    <section :class="['crm-card flex-col min-h-0 overflow-hidden', activeId ? 'hidden lg:flex' : 'flex']">
      <div class="p-3 space-y-2 border-b border-line">
        <SearchBox v-model="q" :placeholder="$t('Mavzu, ism, telefon…')" class="sm:w-full!" />
        <ChipGroup v-model="status" :options="chips" size="sm" />
        <BaseSelect v-model="type" :options="typeOpts" />
      </div>
      <ul class="flex-1 overflow-y-auto divide-y divide-line" data-testid="crm-ticket-list">
        <li v-for="tk in list" :key="tk.id">
          <RouterLink :to="`/support/${tk.id}`" :class="['block px-4 py-3 transition', activeId === tk.id ? 'bg-brand-50' : 'hover:bg-[#fafafb]']">
            <div class="flex items-center gap-2">
              <Avatar :name="fullName(user(tk.userId))" size="sm" />
              <div class="min-w-0 flex-1"><p class="text-sm font-semibold truncate">{{ fullName(user(tk.userId)) }}</p><p class="text-[11.5px] text-muted">{{ $t(ROLE_LABELS[tk.role]) }} · {{ $ago(tk.updatedAt) }}</p></div>
              <span v-if="tk.unreadBySupport || tk.status === 'new'" class="min-w-5 h-5 px-1 grid place-items-center rounded-full bg-brand text-white text-[11px] font-bold">{{ tk.unreadBySupport || '•' }}</span>
            </div>
            <p class="text-[13.5px] font-semibold mt-2 truncate">{{ tk.subject }}</p>
            <p class="text-xs text-muted truncate">{{ tk.messages.at(-1)?.text }}</p>
            <div class="flex items-center gap-1.5 mt-2"><StatusBadge :status="tk.status" /><span class="pill">{{ typeLabel(tk.type) }}</span></div>
          </RouterLink>
        </li>
        <li v-if="!list.length" class="p-8 text-center text-sm text-muted">{{ $t('Murojaat yo‘q') }}</li>
      </ul>
    </section>

    <!-- Chat -->
    <section :class="['crm-card flex-col min-h-0 overflow-hidden', activeId ? 'flex' : 'hidden lg:flex']">
      <div v-if="!ticket" class="flex-1 grid place-items-center text-center p-8">
        <div><RoundIllu kind="support" :size="110" class="mx-auto" /><p class="font-bold mt-3">{{ $t('Murojaatni tanlang') }}</p></div>
      </div>
      <template v-else>
        <header class="flex items-center gap-3 px-4 py-3 border-b border-line">
          <button class="lg:hidden icon-btn" :aria-label="$t('Orqaga')" @click="router.push('/support')"><ArrowLeft class="size-5" /></button>
          <div class="min-w-0 flex-1">
            <p class="font-bold truncate" data-testid="crm-chat-subject">{{ ticket.subject }}</p>
            <p class="text-xs text-muted">#{{ ticket.id.slice(-5).toUpperCase() }} · {{ typeLabel(ticket.type) }} · {{ $dateTime(ticket.createdAt) }}</p>
          </div>
          <StatusBadge :status="ticket.status" />
          <button class="xl:hidden icon-btn" :aria-label="$t('Foydalanuvchi')" @click="infoOpen = true"><UserRound class="size-5" /></button>
          <BaseButton v-if="ticket.status !== 'resolved'" size="sm" variant="soft" :icon="CheckCircle2" data-testid="close-ticket" @click="close">{{ $t('Yopish') }}</BaseButton>
          <BaseButton v-else size="sm" variant="soft" :icon="RotateCcw" @click="reopen">{{ $t('Qayta ochish') }}</BaseButton>
        </header>
        <div ref="scroller" class="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-[#fafbfa]" data-testid="crm-chat" aria-live="polite">
          <template v-for="m in ticket.messages" :key="m.id">
            <p v-if="m.from === 'system'" class="text-center text-[12px] text-muted flex items-center justify-center gap-1.5"><Info class="size-3.5" />{{ $t(m.text) }} · {{ $dateTime(m.at) }}</p>
            <div v-else :class="['flex', m.from === 'support' ? 'justify-end' : 'justify-start']">
              <div :class="['max-w-[78%] rounded-2xl px-3.5 py-2.5 text-[14px] leading-snug shadow-sm', m.from === 'support' ? 'bg-brand text-white rounded-br-md' : 'bg-white border border-line rounded-bl-md']">
                <p v-if="m.from === 'support'" class="text-[11px] font-bold text-white/85 mb-0.5 flex items-center gap-1"><LifeBuoy class="size-3" />Support</p>
                <p v-else class="text-[11px] font-bold text-brand-700 mb-0.5">{{ fullName(owner) }}</p>
                <p v-if="m.text" class="whitespace-pre-line">{{ m.text }}</p>
                <button v-if="m.attachment" class="mt-2 block text-left" @click="openAtt(m.attachment)">
                  <MediaImg :src="m.attachment.url" :alt="m.attachment.name" class="max-h-44 rounded-xl border border-line" />
                  <span class="text-[12px] underline inline-flex items-center gap-1 mt-1"><Paperclip class="size-3" />{{ m.attachment.name }}</span>
                </button>
                <p :class="['text-[10.5px] mt-1 text-right', m.from === 'support' ? 'text-white/75' : 'text-muted']">{{ $dateTime(m.at) }}</p>
              </div>
            </div>
          </template>
        </div>
        <form class="p-3 border-t border-line space-y-2" @submit.prevent="send">
          <div class="flex gap-1.5 overflow-x-auto no-scrollbar">
            <button v-for="r in QUICK" :key="r" type="button" class="shrink-0 h-8 px-3 rounded-full bg-surface hover:bg-brand-50 text-[12px] font-semibold" @click="draft = $t(r)">{{ $t(r).slice(0, 38) }}…</button>
          </div>
          <textarea v-model="draft" rows="3" :placeholder="$t('Javob yozing… (Ctrl+Enter — yuborish)')" class="w-full px-3.5 py-2.5 rounded-xl border border-line outline-none focus:border-brand focus:ring-4 focus:ring-brand/10 resize-none text-[14.5px]" data-testid="crm-reply" @keydown.enter="onEnter" />
          <div class="flex flex-wrap items-center gap-2">
            <label class="text-xs text-muted">{{ $t('Javobdan keyin holat') }}:</label>
            <select v-model="nextStatus" class="h-9 px-2.5 rounded-lg border border-line text-sm" :aria-label="$t('Holat')">
              <option value="answered">{{ $t('Javob berildi') }}</option><option value="in_review">{{ $t('Ko‘rib chiqilmoqda') }}</option><option value="resolved">{{ $t('Hal qilindi') }}</option>
            </select>
            <BaseButton type="submit" class="ml-auto" :icon="SendHorizontal" :loading="sending" :disabled="!draft.trim()" data-testid="crm-reply-send">{{ $t('Yuborish') }}</BaseButton>
          </div>
        </form>
      </template>
    </section>

    <!-- Foydalanuvchi (desktop xl) -->
    <aside class="hidden xl:block crm-card p-4 overflow-y-auto min-h-0">
      <template v-if="owner">
        <div class="text-center"><Avatar :name="fullName(owner)" size="lg" class="mx-auto" /><p class="font-bold mt-2">{{ fullName(owner) }}</p><p class="text-xs text-muted">{{ $t(ROLE_LABELS[owner.role]) }}</p></div>
        <dl class="mt-4 space-y-2 text-sm">
          <div class="flex items-center gap-2"><Phone class="size-4 text-muted" />{{ owner.phone }}</div>
          <div class="flex items-center gap-2"><Send class="size-4 text-muted" />{{ owner.telegram || '—' }}</div>
          <div class="text-muted text-xs">{{ owner.company || owner.university || '' }}</div>
        </dl>
        <RouterLink :to="{ path: '/users', query: { id: owner.id } }" class="mt-3 inline-flex text-sm font-semibold text-brand-700 hover:underline">{{ $t('Profilni ochish') }}</RouterLink>
        <h4 class="font-bold text-sm mt-5 mb-2 flex items-center gap-1.5"><MessageSquareText class="size-4" />{{ $t('Boshqa murojaatlari') }}</h4>
        <ul class="space-y-1.5 text-sm"><li v-for="x in related" :key="x.id"><RouterLink :to="`/support/${x.id}`" class="flex items-center justify-between gap-2 hover:text-brand-700"><span class="truncate">{{ x.subject }}</span><StatusBadge :status="x.status" /></RouterLink></li><li v-if="!related.length" class="text-muted">—</li></ul>
      </template>
      <p v-else class="text-sm text-muted">{{ $t('Murojaat tanlanmagan') }}</p>
    </aside>

    <SideDrawer v-model="infoOpen" :title="fullName(owner)" :subtitle="owner && $t(ROLE_LABELS[owner.role])">
      <div v-if="owner" class="space-y-2 text-sm">
        <p class="flex items-center gap-2"><Phone class="size-4 text-muted" />{{ owner.phone }}</p>
        <p class="flex items-center gap-2"><Send class="size-4 text-muted" />{{ owner.telegram || '—' }}</p>
        <RouterLink :to="{ path: '/users', query: { id: owner.id } }" class="inline-flex font-semibold text-brand-700">{{ $t('Profilni ochish') }}</RouterLink>
      </div>
    </SideDrawer>
  </div>
</template>
