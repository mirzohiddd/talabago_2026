<!-- Ofis ish joyi: kompyuter, qahva va o‘simlik -->
<template>
  <svg viewBox="0 0 220 170" fill="none" stroke="#111" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
    <!-- o‘simlik -->
    <g class="plant">
      <path d="M30 120c-6-14-4-30 4-40M30 120c2-16 10-26 22-30M30 120c-10-8-18-10-24-8" />
      <path d="M34 80c-8 0-12 8-6 12M52 90c-2 8 4 12 10 6M6 112c4 6 12 6 14 0" fill="#fff" />
    </g>
    <path d="M18 120h26l-4 30H22z" fill="#10B981" />
    <!-- stol -->
    <path d="M56 112h150" stroke-width="3" />
    <path d="M70 112v50M192 112v50" />
    <!-- monitor -->
    <rect x="96" y="40" width="80" height="56" rx="5" fill="#fff" />
    <path d="M106 54h40M106 64h56M106 74h30" stroke-width="1.8" stroke="#C9C9CF" />
    <rect x="148" y="70" width="18" height="14" rx="2" fill="#10B981" stroke="none" />
    <path d="M136 96v10M122 108h28" />
    <!-- qahva -->
    <path d="M70 92h18l-2 18H72z" fill="#fff" />
    <path d="M88 96c6 0 6 8 0 8" />
    <g stroke="#10B981" stroke-width="2.2" class="steam"><path d="M76 86c-3-4 3-6 0-10M83 86c-3-4 3-6 0-10" /></g>
    <!-- uchqun -->
    <g stroke="#10B981" stroke-width="3"><path d="M190 30l8-8M198 44h10" /></g>
  </svg>
</template>
<style scoped>
.steam { animation: st 2s ease-in-out infinite; }
.plant { animation: sway 4.5s ease-in-out infinite; transform-origin: 30px 120px; }
@keyframes st { 0% { opacity: 0; transform: translateY(4px) } 50% { opacity: 1 } 100% { opacity: 0; transform: translateY(-4px) } }
@keyframes sway { 0%,100% { transform: rotate(0) } 50% { transform: rotate(-3deg) } }
</style>
