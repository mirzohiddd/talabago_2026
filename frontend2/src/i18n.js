/** TalabaGo Support i18n (o‘z kaliti: talabago_crm_lang) */
import { reactive } from 'vue'
import { createI18n, LOCALES } from '@shared/i18n/index.js'

export const i18n = createI18n({ reactive, storageKey: 'talabago_crm_lang' })
export const { t, tc, ago, date, dateTime, setLocale } = i18n
export { LOCALES }
