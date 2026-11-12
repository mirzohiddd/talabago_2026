<script setup>
import { ref, watch, computed } from 'vue'
import { MapPin, CalendarClock, Eye, CheckCircle2, Send, Wifi, Building2, Heart, Flag, Clock, ArrowRight, ShieldCheck } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import ContactButtons from '@/components/shared/ContactButtons.vue'
import ComplaintModal from './ComplaintModal.vue'
import { JOB_TYPES, WORK_TIMES } from '@/config/roles'
import { salaryText } from '@/utils/format'
import { jobsApi } from '@/services'
import { haptic } from '@/services/telegram'
import { toast } from '@/stores/session'
import { t } from '@/i18n'

const open = defineModel({ type: Boolean })
const props = defineProps({ job: Object, mode: { type: String, default: 'student' } }) // student | viewer
const emit = defineEmits(['changed'])
const router = useRouter()
const step = ref('info') // info | apply | done
const message = ref('')
const sending = ref(false)
const complain = ref(false)
watch(open, (v) => { if (v) { step.value = props.job?.applied ? 'done' : 'info'; message.value = ''; if (props.job?.status === 'active' && props.job?.id) jobsApi.view(props.job.id) } })
const typeLabel = computed(() => JOB_TYPES.find((x) => x.value === props.job?.type)?.label)
const timeLabel = computed(() => WORK_TIMES.find((x) => x.value === props.job?.workTime)?.label)

async function submit() {
  sending.value = true
  try {
    await jobsApi.apply(props.job.id, { message: message.value.trim() })
    haptic.success()
    step.value = 'done'
    emit('changed', { ...props.job, applied: true })
  } catch (e) { toast(e.message || t('Xatolik yuz berdi'), 'error') }
  sending.value = false
}
async function save() {
  const saved = await jobsApi.toggleSave(props.job.id)
  emit('changed', { ...props.job, saved })
  toast(saved ? t('Saqlandi') : t('Saqlanganlardan olib tashlandi'))
}
</script>

<template>
  <BaseModal v-model="open" drawer :title="step === 'apply' ? $t('Ariza yuborish') : $tc(job?.title)" :subtitle="step === 'apply' ? $tc(job?.title) : job?.company">
    <div v-if="job && step === 'info'" class="space-y-5 animate-fade-up" data-testid="job-detail">
      <div class="rounded-2xl bg-brand-25 border border-brand-100 p-4">
        <p class="text-[24px] font-extrabold tracking-tight">{{ salaryText(job) }}</p>
        <div class="flex flex-wrap gap-1.5 mt-2">
          <span class="chip bg-brand text-white">{{ $t(typeLabel) }}</span>
          <span class="chip bg-white"><component :is="job.format === 'online' ? Wifi : Building2" class="size-3.5" />{{ job.format === 'online' ? 'Online' : 'Offline' }}</span>
          <span v-if="timeLabel" class="chip bg-white"><Clock class="size-3.5" />{{ $t(timeLabel) }}</span>
          <span v-if="job.verified" class="chip bg-white text-brand-700" data-testid="verified-badge"><ShieldCheck class="size-3.5" />{{ $t('TalabaGo tekshirgan') }}</span>
        </div>
        <p v-if="job.address" class="flex items-start gap-1.5 text-[13.5px] text-ink-2 mt-2"><MapPin class="size-4 shrink-0 mt-0.5" />{{ job.address }}</p>
      </div>
      <dl class="grid grid-cols-2 gap-3 text-sm">
        <div class="info"><dt><MapPin class="size-4" />{{ $t('Manzil') }}</dt><dd>{{ job.format === 'online' ? $t('Masofaviy (online)') : `${$t(job.district || '')}, ${$t(job.city)}` }}</dd></div>
        <div class="info"><dt><CalendarClock class="size-4" />{{ $t('Ish jadvali') }}</dt><dd>{{ $tc(job.schedule) || '—' }}</dd></div>
        <div class="info"><dt><Eye class="size-4" />{{ $t('Ko‘rishlar') }}</dt><dd class="tabular-nums">{{ job.views || 0 }}</dd></div>
        <div class="info"><dt><Clock class="size-4" />{{ $t('Joylandi') }}</dt><dd>{{ $ago(job.createdAt) }}</dd></div>
      </dl>
      <section>
        <h4 class="font-bold mb-1.5">{{ $t('Tavsif') }}</h4>
        <p class="text-ink-2 text-[15px] leading-relaxed whitespace-pre-line">{{ $tc(job.description) }}</p>
      </section>
      <section v-if="job.requirements?.length">
        <h4 class="font-bold mb-2">{{ $t('Talablar') }}</h4>
        <ul class="space-y-2">
          <li v-for="r in job.requirements" :key="r" class="flex gap-2 text-[15px] text-ink-2"><CheckCircle2 class="size-[18px] text-brand-600 shrink-0 mt-0.5" />{{ $tc(r) }}</li>
        </ul>
      </section>
      <section>
        <h4 class="font-bold mb-2">{{ $t('Bog‘lanish') }}</h4>
        <ContactButtons :phone="job.phone" :telegram="job.telegram" />
        <p v-if="!job.phone && !job.telegram" class="text-[13.5px] text-muted">{{ $t('Aloqa ma’lumotlari ko‘rsatilmaydi. Ariza yuboring — javobni ilovada olasiz.') }}</p>
      </section>
      <button v-if="mode === 'student'" class="inline-flex items-center gap-1.5 text-[13px] font-semibold text-muted hover:text-danger" data-testid="complain" @click="complain = true"><Flag class="size-4" />{{ $t('Shikoyat qilish') }}</button>
    </div>

    <div v-else-if="step === 'apply'" class="space-y-4 animate-fade-up">
      <p class="text-[15px] text-ink-2">{{ $t('Ish beruvchiga profilingiz (ism, o‘quv yurti, ko‘nikmalar, CV) va qisqa xabaringiz yuboriladi.') }}</p>
      <BaseTextarea v-model="message" :label="$t('Xabar (ixtiyoriy)')" :placeholder="$t('Masalan: kechki smenalarda ishlay olaman, tajribam bor...')" :rows="5" :maxlength="400" data-testid="apply-message" />
    </div>

    <div v-else-if="step === 'done'" class="py-6 text-center animate-pop" data-testid="apply-done">
      <RoundIllu kind="office" :size="120" class="mx-auto" />
      <h3 class="text-xl font-extrabold mt-4">{{ $t('Ariza yuborildi!') }}</h3>
      <p class="text-muted mt-1">{{ $t('Holatini “Arizalarim” bo‘limida kuzatishingiz mumkin.') }}</p>
    </div>

    <template #footer>
      <div v-if="mode === 'student' && step === 'info'" class="flex gap-2">
        <BaseButton variant="soft" :aria-label="job?.saved ? $t('Saqlanganlardan olib tashlash') : $t('Saqlash')" @click="save"><Heart class="size-[18px]" :class="job?.saved && 'text-brand-600'" :fill="job?.saved ? 'currentColor' : 'none'" /></BaseButton>
        <BaseButton block class="flex-1" :icon="Send" data-testid="apply-btn" @click="step = 'apply'">{{ $t('Ariza yuborish') }}</BaseButton>
      </div>
      <div v-else-if="step === 'apply'" class="flex gap-2">
        <BaseButton variant="soft" @click="step = 'info'">{{ $t('Orqaga') }}</BaseButton>
        <BaseButton block class="flex-1" :loading="sending" :icon="Send" data-testid="apply-submit" @click="submit">{{ $t('Yuborish') }}</BaseButton>
      </div>
      <div v-else-if="step === 'done'" class="flex gap-2">
        <BaseButton variant="soft" class="flex-1" @click="open = false">{{ $t('Yopish') }}</BaseButton>
        <BaseButton class="flex-1" :icon-right="ArrowRight" @click="open = false; router.push('/student/applications')">{{ $t('Arizalarim') }}</BaseButton>
      </div>
      <BaseButton v-else block variant="soft" @click="open = false">{{ $t('Yopish') }}</BaseButton>
    </template>
  </BaseModal>
  <ComplaintModal v-model="complain" :target="job && { type: 'job', id: job.id, label: `${job.title} · ${job.company}` }" />
</template>

<style scoped>
@reference "../../style.css";
.chip { @apply inline-flex items-center gap-1 h-7 px-2.5 rounded-full text-[12.5px] font-semibold; }
.info { @apply rounded-xl bg-surface p-3; }
.info dt { @apply flex items-center gap-1.5 text-xs text-muted font-semibold; }
.info dd { @apply mt-1 font-semibold text-[14px]; }
</style>