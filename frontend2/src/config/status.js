/** CRM holatlari va yorliqlari — umumiy domen (shared/domain.js) dan */
export { STATUS, ROLE_LABELS, PRIORITY, JOB_TYPES, JOB_FORMATS, HOUSE_TYPES, AUDIENCES, WORK_TIMES, SALARY_PERIODS, AMENITIES, TICKET_TYPES, SHIFTS, RENT_TERMS, CITIES, CITY_LIST, LISTING_STATUSES, APPLICATION_STATUSES, REQUEST_STATUSES, TICKET_STATUSES, COMPLAINT_STATUSES, QUIZ_SIZE } from '@shared/domain.js'
import { JOB_TYPES, HOUSE_TYPES } from '@shared/domain.js'
export const JOB_TYPE_LABELS = Object.fromEntries(JOB_TYPES.map((x) => [x.value, x.label]))
export const HOUSE_TYPE_LABELS = Object.fromEntries(HOUSE_TYPES.map((x) => [x.value, x.label]))
export const PERIOD_SHORT = { hour: 'soat', day: 'kun', week: 'hafta', month: 'oy' }
