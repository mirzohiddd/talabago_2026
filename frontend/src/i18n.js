/** Mini App i18n: tanlangan til localStorage’da (talabago_lang), backendda — users.language */
import { reactive } from 'vue'
import { createI18n, LOCALES } from '@shared/i18n/index.js'

export const i18n = createI18n({ reactive, storageKey: 'talabago_lang' })
export const { t, tc, ago, date, dateTime, setLocale } = i18n
export { LOCALES }
