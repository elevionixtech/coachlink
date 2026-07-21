// Type aliases over the OpenAPI-generated schema (src/api/schema.d.ts).
// Regenerate with: npm run gen:api  (server must be running on :8200)
import type { components } from './schema'

type S = components['schemas']

export type TokenPair = S['TokenPair']
export type UserOut = S['UserOut']
export type OrgSettingsOut = S['OrgSettingsOut']
export type PlanOut = S['PlanOut']
export type MemberOut = S['MemberOut']
export type AdminOrgOut = S['AdminOrgOut']
export type ServiceOut = S['ServiceOut']
export type ServiceIn = S['ServiceIn']
export type DeliverableIn = S['DeliverableIn']
export type ClientOut = S['ClientOut']
export type ClientIn = S['ClientIn']
export type NoteOut = S['NoteOut']
export type InstructorOut = S['InstructorOut']
export type InstructorIn = S['InstructorIn']
export type LocationOut = S['LocationOut']
export type LocationIn = S['LocationIn']
export type BatchOut = S['BatchOut']
export type BatchIn = S['BatchIn']
export type EnrollmentOut = S['EnrollmentOut']
export type SubscriptionOut = S['SubscriptionOut']
export type InvoiceOut = S['InvoiceOut']
export type InvoicePage = S['InvoicePage']
export type DashboardOut = S['DashboardOut']

export type Page<T> = { items: T[]; next_cursor: number | null }

export const SERVICE_TYPES = ['Subscription', 'Usage Based', 'One Time', 'Project Based'] as const
export const DELIVERY_MODES = ['Offline', 'Online', 'Hybrid', 'Self Service'] as const
export const BILLING_INTERVALS = ['N/A', 'Monthly', 'Weekly', 'Quarterly', 'Semi-Annual', 'Annual'] as const
export const CANCELLATION_POLICIES = ['Non-Refundable', 'Flexible', 'Moderate', 'Strict'] as const
export const PRICING_OPTIONS = ['Corporate Plan', 'Family Plan', 'Other'] as const
export const GENDERS = ['Female', 'Male', 'Non-binary', 'Prefer not to say'] as const
export const LIFECYCLE_STAGES = ['Lead', 'Prospect', 'Customer', 'Lapsed'] as const
export const ACCOUNT_TYPES = ['Individual', 'Corporate', 'Family'] as const
export const LEAD_SOURCES = ['Walk-in', 'Referral', 'Instagram', 'Website', 'Corporate tie-up', 'Event', 'Other'] as const
export const NOTE_CHANNELS = ['Call', 'WhatsApp', 'Email', 'In person'] as const
export const LOCATION_TYPES = ['Studio', 'Center', 'Branch', 'Campus', 'Clinic', 'Other'] as const
export const DELIVERABLE_UNITS = ['sessions', 'classes', 'hours', 'days'] as const
export const BATCH_STATUSES = ['active', 'inactive', 'upcoming', 'completed'] as const
