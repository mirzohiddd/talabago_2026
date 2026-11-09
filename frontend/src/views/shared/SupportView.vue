<script setup>
/**
 * TalabaGo Support (barcha rollar). Murojaat → TalabaGo Support “Support” inbox’iga tushadi.
 * Desktop: chapda murojaatlar, o‘ngda chat. Mobil: ro‘yxat → alohida chat sahifasi.
 */
import PageIntro from '@/components/layout/PageIntro.vue'
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, ArrowLeft, Paperclip, SendHorizontal, ImagePlus, X, LifeBuoy, CheckCircle2, Info } from 'lucide-vue-next'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import MediaImg from '@/components/ui/MediaImg.vue'
import { supportApi, uploadFile } from '@/services'
import { TICKET_TYPES, useOptions } from '@/config/roles'
import { session, toast } from '@/stores/session'
import { resolveMedia } from '@/composables/useMediaUrl'
import { openLink } from '@/services/telegram'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()
const base = computed(() => `/${session.role}/support`)
const tickets = ref([])
const loading = ref(true)
async function loadList() {
  try { tickets.value = await supportApi.list() } catch (e) { toast(e.message, 'error') } finally { loading.value = false }
}
onMounted(loadList)
// Javoblar real vaqtga yaqin: ochiq chat har 10 soniyada, ro‘yxat har 30 soniyada yangilanadi
let tick = 0
const poll = setInterval(async () => {
  if (document.visibilityState !== 'visible') return
  tick++
  if (activeId.value && ticket.value) {
    const fresh = await supportApi.get(activeId.value).catch(() => null)
    if (fresh && fresh.messages.length !== ticket.value.messages.length) {
      ticket.value = fresh
      if (fresh.unreadByUser) supportApi.markRead(fresh.id).catch(() => {})
      await nextTick(); scrollDown()
    } else if (fresh) ticket.value = fresh
  }
  if (tick % 3 === 0) loadList()
}, 10000)
onBeforeUnmount(() => clearInterval(poll))

const typeOpts = useOptions(TICKET_TYPES)
const typeLabel = (v) => t(TICKET_TYPES.find((x) => x.value === v)?.label || v)

// ---- Ochiq chat ----
const activeId = computed(() => route.params.id || null)
const ticket = ref(null)
const chatLoading = ref(false)
const scroller = ref(null)
async function loadTicket(id) {
  if (!id) { ticket.value = null; return }
  chatLoading.value = true
  try { ticket.value = await supportApi.get(id) } catch (e) { ticket.value = null; toast(e.message, 'error') } finally { chatLoading.value = false }
  if (ticket.value?.unreadByUser) { await supportApi.markRead(id); loadList() }
  await nextTick(); scrollDown()
}
watch(activeId, loadTicket, { immediate: true })
function scrollDown() { const el = scroller.value; if (el) el.scrollTop = el.scrollHeight }

// ---- Yangi murojaat ----
const newOpen = ref(false)
const form = ref({ type: 'technical', subject: '', text: '', attachment: null })
const shotPreview = ref(null)
const errors = ref({})
const creating = ref(false)
const shotInput = ref(null)
function openNew() { form.value = { type: 'technical', subject: '', text: '', attachment: null }; shotPreview.value = null; errors.value = {}; newOpen.value = true }
async function pickShot(e, target = 'new') {
  const f = e.target.files?.[0]; e.target.value = ''
  if (!f) return
  if (!/^image\//.test(f.type) || f.size > 5 * 1048576) return toast(t('Skrinshot: rasm, 5 MB gacha'), 'error')
  const att = { name: f.name, url: await uploadFile(f, 'shot') }
  if (target === 'new') { form.value.attachment = att; shotPreview.value = await resolveMedia(att.url) }
  else { draftAtt.value = att; draftPreview.value = await resolveMedia(att.url) }
}
async function create() {
  errors.value = {}
  if (form.value.subject.trim().length < 4) errors.value.subject = t('Kamida {n} ta belgi', { n: 4 })
  if (form.value.text.trim().length < 10) errors.value.text = t('Kamida {n} ta belgi', { n: 10 })
  if (Object.keys(errors.value).length) return
  creating.value = true
  const tk = await supportApi.create({ ...form.value, subject: form.value.subject.trim(), text: form.value.text.trim() })
  creating.value = false; newOpen.value = false
  toast(t('Murojaat yuborildi'))
  await loadList()
  router.push(`${base.value}/${tk.id}`)
}

// ---- Xabar yozish ----
const draft = ref('')
const draftAtt = ref(null)
const draftPreview = ref(null)
const sending = ref(false)
const chatInput = ref(null)
async function send() {
  if (!draft.value.trim() && !draftAtt.value) return
  sending.value = true
  ticket.value = await supportApi.send(ticket.value.id, { text: draft.value.trim(), attachment: draftAtt.value })
  draft.value = ''; draftAtt.value = null; draftPreview.value = null
  sending.value = false
  loadList()
  await nextTick(); scrollDown()
}
function onEnter(e) { if (!e.shiftKey) { e.preventDefault(); send() } }
</script>

<template>
  <div class="page lg:max-w-6xl lg:pb-8!">
    <div :class="['lg:grid lg:grid-cols-[360px_minmax(0,1fr)] lg:gap-5 lg:h-[calc(100dvh-64px-56px)]']">
      <!-- ===== Ro‘yxat ===== -->
      <section :class="['lg:flex flex-col min-h-0', activeId && 'hidden']">
        <PageIntro class="mb-4" title="TalabaGo Support" subtitle="Muammo bo‘lsa yozing — javob shu yerda keladi.">
          <BaseButton size="sm" :icon="Plus" data-testid="new-ticket" @click="openNew">{{ $t('Yangi murojaat') }}</BaseButton>
        </PageIntro>
        <SkeletonCard v-if="loading" :count="3" />
        <EmptyState v-else-if="!tickets.length" :title="$t('Murojaatlar yo‘q')" :text="$t('Savol yoki muammo bo‘lsa, yangi murojaat yarating.')" illu="chat">
          <BaseButton :icon="Plus" @click="openNew">{{ $t('Murojaat yaratish') }}</BaseButton>
        </EmptyState>
        <ul v-else class="space-y-2 lg:overflow-y-auto lg:pr-1 stagger" data-testid="ticket-list">
          <li v-for="tk in tickets" :key="tk.id">
            <RouterLink :to="`${base}/${tk.id}`" :class="['block card p-3.5 transition', activeId === tk.id ? 'border-brand! bg-brand-25' : 'card-hover']">
              <div class="flex items-center gap-2">
                <p class="font-semibold flex-1 truncate">{{ tk.subject }}</p>
                <span v-if="tk.unreadByUser" class="size-2.5 rounded-full bg-brand" :aria-label="$t('Yangi javob')" />
              </div>
              <p class="text-[12.5px] text-muted truncate mt-0.5">{{ tk.messages.at(-1)?.text }}</p>
              <div class="flex items-center gap-2 mt-2"><StatusBadge :status="tk.status" /><span class="text-xs text-muted">{{ typeLabel(tk.type) }} · {{ $ago(tk.updatedAt) }}</span></div>
            </RouterLink>
          </li>
        </ul>
      </section>

      <!-- ===== Chat ===== -->
      <section :class="['card flex-col min-h-0 overflow-hidden', activeId ? 'flex h-[calc(100dvh-64px-var(--safe-top)-28px)] lg:h-auto -mx-1 lg:mx-0' : 'hidden lg:flex']">
        <div v-if="!activeId" class="flex-1 grid place-items-center text-center p-8">
          <div><RoundIllu kind="support" :size="120" class="mx-auto" /><p class="font-bold text-lg mt-4">{{ $t('Murojaatni tanlang') }}</p><p class="text-sm text-muted">{{ $t('yoki yangisini yarating') }}</p></div>
        </div>
        <template v-else-if="ticket">
          <header class="flex items-center gap-3 px-4 py-3 border-b border-line">
            <button class="lg:hidden size-9 -ml-1 grid place-items-center rounded-full hover:bg-surface" :aria-label="$t('Orqaga')" @click="router.push(base)"><ArrowLeft class="size-5" /></button>
            <div class="min-w-0 flex-1">
              <p class="font-bold truncate" data-testid="chat-subject">{{ ticket.subject }}</p>
              <p class="text-xs text-muted">#{{ ticket.id.slice(-5).toUpperCase() }} · {{ typeLabel(ticket.type) }}</p>
            </div>
            <StatusBadge :status="ticket.status" />
          </header>
          <div ref="scroller" class="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-[#fafbfa]" data-testid="chat-messages" aria-live="polite">
            <template v-for="m in ticket.messages" :key="m.id">
              <p v-if="m.from === 'system'" class="text-center text-[12px] text-muted px-6 flex items-center justify-center gap-1.5"><Info class="size-3.5" />{{ $t(m.text) }}</p>
              <div v-else :class="['flex', m.from === 'user' ? 'justify-end' : 'justify-start']">
                <div :class="['max-w-[82%] rounded-2xl px-3.5 py-2.5 text-[14.5px] leading-snug shadow-sm', m.from === 'user' ? 'bg-brand text-white rounded-br-md' : 'bg-white border border-line rounded-bl-md']">
                  <p v-if="m.from === 'support'" class="text-[11px] font-bold text-brand-700 mb-0.5 flex items-center gap-1"><LifeBuoy class="size-3" />TalabaGo Support</p>
                  <p v-if="m.text" class="whitespace-pre-line">{{ m.text }}</p>
                  <button v-if="m.attachment" class="mt-2 block" @click="resolveMedia(m.attachment.url).then((u) => u && openLink(u))">
                    <MediaImg :src="m.attachment.url" :alt="m.attachment.name" class="max-h-40 rounded-xl bg-white/20" />
                    <span class="text-[12px] underline opacity-90 inline-flex items-center gap-1 mt-1"><Paperclip class="size-3" />{{ m.attachment.name }}</span>
                  </button>
                  <p :class="['text-[10.5px] mt-1 text-right', m.from === 'user' ? 'text-white/75' : 'text-muted']">{{ $dateTime(m.at) }}</p>
                </div>
              </div>
            </template>
          </div>
          <p v-if="ticket.status === 'resolved'" class="px-4 py-2 text-[12.5px] text-success bg-success/8 flex items-center gap-1.5"><CheckCircle2 class="size-4" />{{ $t('Murojaat hal qilingan. Yangi xabar yozsangiz, qayta ochiladi.') }}</p>
          <form class="p-3 border-t border-line safe-bottom lg:pb-3" @submit.prevent="send">
            <div v-if="draftPreview" class="relative inline-block mb-2"><img :src="draftPreview" alt="" class="h-16 rounded-lg" /><button type="button" class="absolute -right-2 -top-2 size-6 rounded-full bg-ink text-white grid place-items-center" :aria-label="$t('O‘chirish')" @click="draftAtt = null; draftPreview = null"><X class="size-3.5" /></button></div>
            <div class="flex items-end gap-2">
              <button type="button" class="size-11 shrink-0 grid place-items-center rounded-xl hover:bg-surface text-ink-2" :aria-label="$t('Skrinshot biriktirish')" @click="chatInput.click()"><Paperclip class="size-5" /></button>
              <textarea v-model="draft" rows="1" :placeholder="$t('Xabar yozing...')" class="flex-1 min-h-11 max-h-32 px-3.5 py-2.5 rounded-xl border border-line outline-none focus:border-brand resize-none text-[15px]" data-testid="chat-input" @keydown.enter="onEnter" />
              <BaseButton type="submit" :loading="sending" :disabled="!draft.trim() && !draftAtt" :aria-label="$t('Yuborish')" class="w-11 px-0!" data-testid="chat-send"><SendHorizontal class="size-5" /></BaseButton>
            </div>
            <input ref="chatInput" type="file" accept="image/*" class="hidden" @change="pickShot($event, 'chat')" />
          </form>
        </template>
        <div v-else-if="chatLoading" class="p-6"><SkeletonCard :count="2" /></div>
        <EmptyState v-else :title="$t('Murojaat topilmadi')" text="" illu="chat" />
      </section>
    </div>

    <!-- Yangi murojaat -->
    <BaseModal v-model="newOpen" :title="$t('Yangi murojaat')" :subtitle="$t('Javob shu chatga va bildirishnomalarga keladi')">
      <div class="space-y-4">
        <div><span class="label">{{ $t('Murojaat turi') }}</span><ChipGroup v-model="form.type" :options="typeOpts" size="sm" wrap /></div>
        <BaseInput v-model="form.subject" :label="$t('Mavzu')" :placeholder="$t('Qisqacha: nima bo‘ldi?')" required :maxlength="80" :error="errors.subject" data-testid="t-subject" />
        <BaseTextarea v-model="form.text" :label="$t('Xabar')" :placeholder="$t('Muammoni batafsil yozing: qaysi sahifada, nima qilganingizda...')" :rows="5" :maxlength="1000" required :error="errors.text" data-testid="t-text" />
        <div>
          <span class="label">{{ $t('Skrinshot (ixtiyoriy)') }}</span>
          <div v-if="shotPreview" class="relative inline-block"><img :src="shotPreview" alt="" class="h-24 rounded-xl border border-line" /><button type="button" class="absolute -right-2 -top-2 size-6 rounded-full bg-ink text-white grid place-items-center" :aria-label="$t('O‘chirish')" @click="form.attachment = null; shotPreview = null"><X class="size-3.5" /></button></div>
          <button v-else type="button" class="h-11 px-4 rounded-xl border-2 border-dashed border-line hover:border-brand text-sm font-semibold inline-flex items-center gap-2" @click="shotInput.click()"><ImagePlus class="size-4 text-brand-600" />{{ $t('Rasm biriktirish') }}</button>
          <input ref="shotInput" type="file" accept="image/*" class="hidden" data-testid="t-shot" @change="pickShot($event, 'new')" />
        </div>
      </div>
      <template #footer><BaseButton block :loading="creating" :icon="SendHorizontal" data-testid="t-submit" @click="create">{{ $t('Yuborish') }}</BaseButton></template>
    </BaseModal>
  </div>
</template>
