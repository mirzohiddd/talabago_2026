<script setup>
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { MapPin, BedDouble, Users, Ruler, CheckCircle2, Send, Heart, Flag, ChevronLeft, ChevronRight, ArrowRight, UserRound, DoorOpen, ShieldCheck } from 'lucide-vue-next'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import MapPreview from '@/components/shared/MapPreview.vue'
import ContactButtons from '@/components/shared/ContactButtons.vue'
import ComplaintModal from './ComplaintModal.vue'
import { HOUSE_TYPES, AUDIENCES, RENT_TERMS, useOptions } from '@/config/roles'
import { priceText } from '@/utils/format'
import { housingApi } from '@/services'
import { useMediaList } from '@/composables/useMediaUrl'
import { haptic } from '@/services/telegram'
import { toast } from '@/stores/session'
import { t } from '@/i18n'

const open = defineModel({ type: Boolean })
const props = defineProps({ house: Object, mode: { type: String, default: 'student' } }) // student | viewer
const emit = defineEmits(['changed'])
const router = useRouter()
const step = ref('info')
const photos = useMediaList(() => props.house?.photos)
const idx = ref(0)
const strip = ref(null)
const complain = ref(false)
const form = ref({ moveIn: '', term: '6', message: '' })
const errors = ref({})
const sending = ref(false)
const termOpts = useOptions(RENT_TERMS)
const today = new Date().toISOString().slice(0, 10)

watch(open, (v) => { if (v) { step.value = props.house?.requested ? 'done' : 'info'; idx.value = 0; form.value = { moveIn: '', term: '6', message: '' }; errors.value = {}; if (props.house?.status === 'active' && props.house?.id) housingApi.view(props.house.id) } })
const typeLabel = computed(() => HOUSE_TYPES.find((x) => x.value === props.house?.type)?.label)
const audience = computed(() => AUDIENCES.find((x) => x.value === props.house?.audience)?.label)
const full = computed(() => props.house && (props.house.occupancy === 'occupied' || !props.house.freeSpots))

function onScroll() { const el = strip.value; if (el) idx.value = Math.round(el.scrollLeft / el.clientWidth) }
function goTo(i) { const el = strip.value; if (el) el.scrollTo({ left: i * el.clientWidth, behavior: 'smooth' }) }

async function submit() {
  errors.value = {}
  if (!form.value.moveIn) errors.value.moveIn = t('Majburiy maydon')
  if (Object.keys(errors.value).length) return
  sending.value = true
  try {
    await housingApi.request(props.house.id, { ...form.value, message: form.value.message.trim() })
    haptic.success()
    step.value = 'done'
    emit('changed', { ...props.house, requested: true })
  } catch (e) { toast(e.message || t('Xatolik yuz berdi'), 'error') }
  sending.value = false
}
async function save() {
  const saved = await housingApi.toggleSave(props.house.id)
  emit('changed', { ...props.house, saved })
  toast(saved ? t('Saqlandi') : t('Saqlanganlardan olib tashlandi'))
}
</script>

<template>
  <BaseModal v-model="open" drawer :title="step === 'request' ? $t('Ijara so‘rovi') : $tc(house?.title)" :subtitle="step === 'request' ? $tc(house?.title) : undefined">
    <div v-if="house && step === 'info'" class="space-y-5 animate-fade-up" data-testid="house-detail">
      <!-- Galereya (swipe) -->
      <div class="relative -mx-5 sm:mx-0 sm:rounded-2xl overflow-hidden bg-brand-50">
        <div ref="strip" class="flex overflow-x-auto snap-x snap-mandatory no-scrollbar aspect-[16/10]" data-testid="gallery" @scroll.passive="onScroll">
          <img v-for="(p, i) in photos" :key="i" :src="p" :alt="`${house.title} — ${i + 1}`" class="w-full h-full shrink-0 object-cover snap-center" :loading="i ? 'lazy' : 'eager'" />
        </div>
        <span class="absolute right-3 top-3 h-7 px-2.5 rounded-full bg-ink/70 text-white text-xs font-semibold grid place-items-center tabular-nums">{{ idx + 1 }} / {{ photos.length }}</span>
        <button v-if="idx > 0" class="nav left-3" :aria-label="$t('Oldingi rasm')" @click="goTo(idx - 1)"><ChevronLeft class="size-5" /></button>
        <button v-if="idx < photos.length - 1" class="nav right-3" :aria-label="$t('Keyingi rasm')" @click="goTo(idx + 1)"><ChevronRight class="size-5" /></button>
        <div class="absolute bottom-3 inset-x-0 flex justify-center gap-1.5">
          <button v-for="(p, i) in photos" :key="i" :class="['h-1.5 rounded-full transition-all', i === idx ? 'w-5 bg-white' : 'w-1.5 bg-white/60']" :aria-label="`${i + 1}`" @click="goTo(i)" />
        </div>
      </div>

      <div>
        <p class="text-[24px] font-extrabold tracking-tight">{{ priceText(house) }}</p>
        <p class="mt-1 text-[14px] text-ink-2 flex items-center gap-1.5"><MapPin class="size-4 text-muted" />{{ $tc(house.address) }} · {{ $t(house.district) }}, {{ $t(house.city) }}</p>
        <div class="flex flex-wrap gap-1.5 mt-3">
          <span class="chip bg-brand text-white">{{ $t(typeLabel) }}</span>
          <span :class="['chip', full ? 'bg-ink text-white' : 'bg-brand-50 text-brand-700']"><DoorOpen class="size-3.5" />{{ full ? $t('Band') : $t('Bo‘sh') }}</span>
          <span class="chip bg-surface">{{ $t(audience) }}</span>
        </div>
      </div>
      <dl class="grid grid-cols-3 gap-2.5 text-sm">
        <div class="info"><dt><BedDouble class="size-4" />{{ $t('Xonalar') }}</dt><dd>{{ house.rooms }}</dd></div>
        <div class="info"><dt><Ruler class="size-4" />{{ $t('Maydon') }}</dt><dd>{{ house.area }} m²</dd></div>
        <div class="info"><dt><Users class="size-4" />{{ $t('Bo‘sh joylar') }}</dt><dd>{{ house.freeSpots }} / {{ house.capacity }}</dd></div>
      </dl>
      <section v-if="house.amenities?.length">
        <h4 class="font-bold mb-2">{{ $t('Qulayliklar') }}</h4>
        <ul class="grid grid-cols-2 gap-2">
          <li v-for="a in house.amenities" :key="a" class="flex items-center gap-2 text-[14px] text-ink-2"><CheckCircle2 class="size-[18px] text-brand-600 shrink-0" />{{ $t(a) }}</li>
        </ul>
      </section>
      <section>
        <h4 class="font-bold mb-1.5">{{ $t('Tavsif') }}</h4>
        <p class="text-ink-2 text-[15px] leading-relaxed whitespace-pre-line">{{ $tc(house.description) }}</p>
      </section>
      <section v-if="house.lat">
        <h4 class="font-bold mb-2">{{ $t('Joylashuv') }}</h4>
        <MapPreview :lat="house.lat" :lng="house.lng" :label="`${$t(house.district)}, ${$t(house.city)}`" />
      </section>
      <section>
        <h4 class="font-bold mb-2">{{ $t('Uy egasi') }}</h4>
        <p class="flex items-center gap-2 text-[15px] font-semibold mb-2"><UserRound class="size-[18px] text-muted" />{{ house.owner?.name }}
          <span v-if="house.verified" class="inline-flex items-center gap-1 px-2 h-6 rounded-full bg-brand-50 text-brand-700 text-[12px] font-bold" data-testid="verified-badge"><ShieldCheck class="size-3.5" />{{ $t('TalabaGo tekshirgan') }}</span></p>
        <ContactButtons :phone="house.phone" :telegram="house.telegram" />
        <p v-if="!house.phone && !house.telegram" class="text-[13.5px] text-muted">{{ $t('Aloqa ma’lumotlari ko‘rsatilmaydi. So‘rov yuboring — javobni ilovada olasiz.') }}</p>
      </section>
      <button v-if="mode === 'student'" class="inline-flex items-center gap-1.5 text-[13px] font-semibold text-muted hover:text-danger" @click="complain = true"><Flag class="size-4" />{{ $t('Shikoyat qilish') }}</button>
    </div>

    <form v-else-if="step === 'request'" class="space-y-4 animate-fade-up" novalidate @submit.prevent="submit">
      <div class="grid grid-cols-2 gap-3">
        <BaseInput v-model="form.moveIn" type="date" :min="today" :label="$t('Ko‘chib o‘tish sanasi')" required :error="errors.moveIn" data-testid="move-in" />
        <BaseSelect v-model="form.term" :label="$t('Ijara muddati')" :options="termOpts" />
      </div>
      <BaseTextarea v-model="form.message" :label="$t('Xabar (ixtiyoriy)')" :placeholder="$t('Masalan: dugonam bilan birga yashamoqchimiz...')" :rows="4" :maxlength="400" />
      <p class="text-xs text-muted">{{ $t('Uy egasiga profilingiz va telefon raqamingiz ko‘rinadi.') }}</p>
    </form>

    <div v-else-if="step === 'done'" class="py-6 text-center animate-pop" data-testid="request-done">
      <RoundIllu kind="key" :size="120" class="mx-auto" />
      <h3 class="text-xl font-extrabold mt-4">{{ $t('So‘rov yuborildi!') }}</h3>
      <p class="text-muted mt-1">{{ $t('Uy egasi javobini “Arizalarim → Ijara so‘rovlarim”da ko‘rasiz.') }}</p>
    </div>

    <template #footer>
      <div v-if="mode === 'student' && step === 'info'" class="flex gap-2">
        <BaseButton variant="soft" :aria-label="house?.saved ? $t('Saqlanganlardan olib tashlash') : $t('Saqlash')" @click="save"><Heart class="size-[18px]" :class="house?.saved && 'text-brand-600'" :fill="house?.saved ? 'currentColor' : 'none'" /></BaseButton>
        <BaseButton block class="flex-1" :icon="Send" :disabled="full" data-testid="request-btn" @click="step = 'request'">{{ full ? $t('Hozircha bo‘sh joy yo‘q') : $t('Ijara so‘rovi yuborish') }}</BaseButton>
      </div>
      <div v-else-if="step === 'request'" class="flex gap-2">
        <BaseButton variant="soft" @click="step = 'info'">{{ $t('Orqaga') }}</BaseButton>
        <BaseButton block class="flex-1" :loading="sending" :icon="Send" data-testid="request-submit" @click="submit">{{ $t('Yuborish') }}</BaseButton>
      </div>
      <div v-else-if="step === 'done'" class="flex gap-2">
        <BaseButton variant="soft" class="flex-1" @click="open = false">{{ $t('Yopish') }}</BaseButton>
        <BaseButton class="flex-1" :icon-right="ArrowRight" @click="open = false; router.push('/student/applications?tab=requests')">{{ $t('Arizalarim') }}</BaseButton>
      </div>
      <BaseButton v-else block variant="soft" @click="open = false">{{ $t('Yopish') }}</BaseButton>
    </template>
  </BaseModal>
  <ComplaintModal v-model="complain" :target="house && { type: 'house', id: house.id, label: house.title }" />
</template>

<style scoped>
@reference "../../style.css";
.chip { @apply inline-flex items-center gap-1 h-7 px-2.5 rounded-full text-[12.5px] font-semibold; }
.info { @apply rounded-xl bg-surface p-3; }
.info dt { @apply flex items-center gap-1.5 text-xs text-muted font-semibold; }
.info dd { @apply mt-1 font-bold text-[15px]; }
.nav { @apply absolute top-1/2 -translate-y-1/2 size-9 rounded-full bg-white/90 place-items-center shadow hidden sm:grid hover:bg-white; }
</style>