<script setup>
/** <img>, lekin src "idb:<kalit>" bo‘lsa IndexedDB’dan o‘qiladi */
import { useMediaUrl } from '@/composables/useMediaUrl'
const props = defineProps({ src: String, alt: { type: String, default: '' } })
const url = useMediaUrl(() => props.src)
</script>
<template><img v-if="url" :src="url" :alt="alt" loading="lazy" decoding="async" /></template>