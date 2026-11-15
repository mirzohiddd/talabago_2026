<script setup>
/** Chatlar nazorati (Support): talaba ↔ ish beruvchi suhbatlarini ko‘rish, nojo‘ya xabarni yashirish, suhbatni cheklash */
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Lock, Unlock, EyeOff, Eye, MessageCircle } from 'lucide-vue-next'
import PageHeader from '@/components/crm/PageHeader.vue'
import SearchBox from '@/components/crm/SearchBox.vue'
import Pagination from '@/components/crm/Pagination.vue'
import SkeletonRows from '@/components/crm/SkeletonRows.vue'
import SideDrawer from '@/components/crm/SideDrawer.vue'
import Avatar from '@/components/ui/Avatar.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { crmStore, ensureCrmLoaded, crmApi } from '@/services/crm'
import { toast } from '@/stores/toast'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()
const loading = ref(!crmStore.loaded)
ensureCrmLoaded().then(() => (loading.value = false))
const q = ref('')
const page = ref(1)
const PER = 15
watch(q, () => (page.value = 1))
const list = computed(() => {
  const s = q.value.trim().toLowerCase()
  return crmStore.chats.filter((c) => !s || [c.studentName, c.employerName, c.jobTitle].some((v) => v?.toLowerCase().includes(s)))
})
const rows = computed(() => list.value.slice((page.value - 1) * PER, page.value * PER))

const current = ref(null)
const drawer = ref(false)
const msgs = ref([])
const msgLoading = ref(false)
async function open(c) {
  current.value = c; drawer.value = true; msgLoading.value = true
  router.replace({ query: { id: c.id } })
  try { msgs.value = await crmApi.chatMessages(c.id) } catch (e) { toast(t(e.message), 'error') }
  msgLoading.value = false
}
watch(drawer, (v) => { if (!v) router.replace({ query: {} }) })
watch(() => [loading.value, route.query.id], () => {
  const c = !loading.value && route.query.id && crmStore.chats.find((x) => x.id === route.query.id)
  if (c && current.value?.id !== c.id) open(c)
}, { immediate: true })
const who = (m) => (m.fromId === current.value?.studentId ? current.value.studentName : current.value?.employerName)
async function toggleHide(m) {
  try { await crmApi.setMessageHidden(m.id, !m.hidden); m.hidden = !m.hidden; toast(m.hidden ? t('Xabar yashirildi') : t('Xabar qayta ko‘rsatildi')) }
  catch (e) { toast(t(e.message), 'error') }
}
async function toggleLock() {
  const v = !current.value.locked
  try { await crmApi.setChatLocked(current.value.id, v); current.value.locked = v; toast(v ? t('Suhbat cheklandi') : t('Suhbat ochildi')) }
  catch (e) { toast(t(e.message), 'error') }
}
</script>

<template>
  <div>
    <PageHeader :title="$t('Chatlar nazorati')" illu="mail"><SearchBox v-model="q" :placeholder="$t('Talaba, ish beruvchi yoki vakansiya…')" /></PageHeader>
    <div class="crm-card overflow-hidden">
      <SkeletonRows v-if="loading" :rows="6" :cols="5" />
      <EmptyState v-else-if="!list.length" :title="$t('Hali suhbat yo‘q')" :text="$t('Talaba ishga ariza yuborganda suhbat avtomatik ochiladi.')" illu="mail" />
      <div v-else class="overflow-x-auto">
        <table class="crm-table min-w-[860px]" data-testid="crm-chats-table">
          <thead><tr><th>{{ $t('Talaba') }}</th><th>{{ $t('Ish beruvchi') }}</th><th>{{ $t('Vakansiya') }}</th><th>{{ $t('Xabarlar') }}</th><th>{{ $t('Oxirgi xabar') }}</th><th>{{ $t('Holat') }}</th></tr></thead>
          <tbody>
            <tr v-for="c in rows" :key="c.id" class="cursor-pointer" @click="open(c)">
              <td class="font-semibold">{{ c.studentName }}</td>
              <td>{{ c.employerName }}</td>
              <td class="max-w-[220px]"><p class="truncate">{{ c.jobTitle }}</p></td>
              <td class="tabular-nums">{{ c.messages }}</td>
              <td class="max-w-[260px]"><p class="truncate text-ink-2">{{ c.lastMessage?.hidden ? $t('(yashirilgan)') : c.lastMessage?.text || '—' }}</p><p class="text-[11px] text-muted">{{ c.lastMessage ? $ago(c.lastMessage.at) : '' }}</p></td>
              <td><span v-if="c.locked" class="inline-flex items-center gap-1 text-xs font-bold text-danger"><Lock class="size-3.5" />{{ $t('Cheklangan') }}</span><span v-else class="text-xs font-semibold text-brand-700">{{ $t('Faol') }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <Pagination v-model="page" :total="list.length" :per-page="PER" />
    </div>

    <SideDrawer v-model="drawer" :title="current && `${current.studentName} ↔ ${current.employerName}`" :subtitle="current?.jobTitle" width="560px">
      <div v-if="current" class="space-y-3" data-testid="crm-chat">
        <div class="flex items-center gap-2">
          <BaseButton size="sm" :variant="current.locked ? 'soft' : 'danger'" :icon="current.locked ? Unlock : Lock" data-testid="chat-lock" @click="toggleLock">{{ current.locked ? $t('Suhbatni ochish') : $t('Suhbatni cheklash') }}</BaseButton>
          <RouterLink :to="{ path: '/applications', query: { id: current.applicationId } }" class="ml-auto text-sm font-semibold text-brand-700 hover:underline">{{ $t('Arizani ochish') }}</RouterLink>
        </div>
        <p v-if="msgLoading" class="text-sm text-muted">{{ $t('Yuklanmoqda...') }}</p>
        <p v-else-if="!msgs.length" class="text-sm text-muted flex items-center gap-2"><MessageCircle class="size-4" />{{ $t('Hali xabar yo‘q') }}</p>
        <ul v-else class="space-y-2">
          <li v-for="m in msgs" :key="m.id" :class="['rounded-xl border p-3', m.hidden ? 'border-danger/30 bg-danger/5' : 'border-line']">
            <div class="flex items-center gap-2 mb-1">
              <Avatar :name="who(m)" size="sm" />
              <b class="text-sm">{{ who(m) }}</b>
              <span class="text-[11px] text-muted">{{ $dateTime(m.createdAt) }}</span>
              <span v-if="m.readAt" class="text-[11px] text-brand-700">✓✓</span>
              <button class="ml-auto icon-btn" :title="m.hidden ? $t('Ko‘rsatish') : $t('Yashirish')" :aria-label="m.hidden ? $t('Ko‘rsatish') : $t('Yashirish')" data-testid="msg-hide" @click="toggleHide(m)"><component :is="m.hidden ? Eye : EyeOff" class="size-4" /></button>
            </div>
            <p class="text-sm whitespace-pre-wrap break-words" :class="m.hidden && 'line-through text-muted'">{{ m.text }}</p>
          </li>
        </ul>
      </div>
    </SideDrawer>
  </div>
</template>
