import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import (
    AccountType,
    BatchStatus,
    BillingInterval,
    CancellationPolicy,
    CapacityPolicy,
    DeliveryMode,
    Gender,
    InvoiceStatus,
    LifecycleStage,
    Role,
    ServiceType,
    SubscriptionStatus,
)

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    next_cursor: int | None = None


# ---------------------------------------------------------------- auth


class LoginIn(BaseModel):
    org_code: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RefreshIn(BaseModel):
    refresh_token: str


class OrgSummary(ORMModel):
    id: uuid.UUID
    name: str
    code: str


class UserOut(ORMModel):
    id: uuid.UUID
    name: str
    username: str
    role: Role
    org: OrgSummary | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------- org & platform


class OrgSettingsOut(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    currency: str
    timezone: str
    invoice_prefix: str
    invoice_grace_days: int
    capacity_policy: CapacityPolicy
    settings: dict
    subscription_starts_on: date | None
    subscription_ends_on: date | None


class OrgSettingsPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    currency: str | None = None
    timezone: str | None = None
    invoice_prefix: str | None = None
    invoice_grace_days: int | None = Field(default=None, ge=0)
    capacity_policy: CapacityPolicy | None = None
    settings: dict | None = None


class PlanIn(BaseModel):
    name: str = Field(min_length=1)
    amount: Decimal = Field(ge=0)
    no_of_days: int = Field(gt=0)
    description: str | None = None


class PlanPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    amount: Decimal | None = Field(default=None, ge=0)
    no_of_days: int | None = Field(default=None, gt=0)
    description: str | None = None


class PlanOut(ORMModel):
    id: uuid.UUID
    name: str
    amount: Decimal
    no_of_days: int
    description: str | None
    orgs_in_use: int = 0


class MemberIn(BaseModel):
    name: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=4)
    role: Role

    @field_validator("role")
    @classmethod
    def no_superadmin(cls, v: Role) -> Role:
        if v == Role.superadmin:
            raise ValueError("created members: admin or staff, never superadmin")
        return v


class MemberOut(ORMModel):
    id: uuid.UUID
    name: str
    username: str
    role: Role
    created_at: datetime


class AdminOrgIn(BaseModel):
    name: str = Field(min_length=1)
    code: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9-]+$")
    admin: MemberIn


class AdminOrgOut(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    plan_id: uuid.UUID | None
    plan_name: str | None = None
    subscription_starts_on: date | None
    subscription_ends_on: date | None
    subscription_state: str
    member_count: int = 0
    client_count: int = 0
    created_at: datetime


class AssignPlanIn(BaseModel):
    plan_id: uuid.UUID
    starts_on: date | None = None


# ---------------------------------------------------------------- services


class DeliverableIn(BaseModel):
    name: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    unit: str = Field(min_length=1)


class DeliverableOut(ORMModel):
    id: uuid.UUID
    name: str
    quantity: int
    unit: str


class ServiceIn(BaseModel):
    name: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    description: str | None = None
    service_type: ServiceType
    delivery_mode: DeliveryMode
    max_capacity: int | None = Field(default=None, ge=0)
    billing_interval: BillingInterval = BillingInterval.na
    rate: Decimal = Field(ge=0)
    cancellation_policy: CancellationPolicy = CancellationPolicy.flexible
    pricing_options: list[str] = []
    deliverables: list[DeliverableIn] = []


class ServicePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    sku: str | None = Field(default=None, min_length=1)
    description: str | None = None
    service_type: ServiceType | None = None
    delivery_mode: DeliveryMode | None = None
    max_capacity: int | None = Field(default=None, ge=0)
    billing_interval: BillingInterval | None = None
    rate: Decimal | None = Field(default=None, ge=0)
    cancellation_policy: CancellationPolicy | None = None
    pricing_options: list[str] | None = None
    deliverables: list[DeliverableIn] | None = None


class ServiceOut(ORMModel):
    id: uuid.UUID
    name: str
    sku: str
    description: str | None
    service_type: ServiceType
    delivery_mode: DeliveryMode
    max_capacity: int | None
    billing_interval: BillingInterval
    rate: Decimal
    cancellation_policy: CancellationPolicy
    pricing_options: list[str]
    deliverables: list[DeliverableOut]
    created_at: datetime


# ---------------------------------------------------------------- clients


class ClientIn(BaseModel):
    name: str = Field(min_length=1)
    name_hint: str | None = None
    phone: str | None = None
    email: str | None = None
    gender: Gender | None = None
    date_of_birth: date | None = None
    lead_source: str | None = None
    lifecycle_stage: LifecycleStage = LifecycleStage.lead
    do_not_contact: bool = False
    do_not_email: bool = False
    do_not_call: bool = False
    address: str | None = None
    work: str | None = None
    description: str | None = None
    account_type: AccountType = AccountType.individual
    company_name: str | None = None
    gstin: str | None = None
    company_contact: str | None = None
    family_link_id: uuid.UUID | None = None


class ClientPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    name_hint: str | None = None
    phone: str | None = None
    email: str | None = None
    gender: Gender | None = None
    date_of_birth: date | None = None
    lead_source: str | None = None
    lifecycle_stage: LifecycleStage | None = None
    do_not_contact: bool | None = None
    do_not_email: bool | None = None
    do_not_call: bool | None = None
    address: str | None = None
    work: str | None = None
    description: str | None = None
    account_type: AccountType | None = None
    company_name: str | None = None
    gstin: str | None = None
    company_contact: str | None = None
    family_link_id: uuid.UUID | None = None


class ClientOut(ORMModel):
    id: uuid.UUID
    name: str
    name_hint: str | None
    phone: str | None
    email: str | None
    gender: Gender | None
    date_of_birth: date | None
    lead_source: str | None
    lifecycle_stage: LifecycleStage
    do_not_contact: bool
    do_not_email: bool
    do_not_call: bool
    address: str | None
    work: str | None
    description: str | None
    account_type: AccountType
    company_name: str | None
    gstin: str | None
    company_contact: str | None
    family_link_id: uuid.UUID | None
    family_link_name: str | None = None
    linked_by: list["ClientRef"] = []
    created_at: datetime


class ClientRef(ORMModel):
    id: uuid.UUID
    name: str


class NoteIn(BaseModel):
    date: date
    channel: str = Field(min_length=1)
    text: str = Field(min_length=1)


class NoteOut(ORMModel):
    id: uuid.UUID
    date: date
    channel: str
    text: str
    author_name: str
    created_at: datetime


# ---------------------------------------------------------------- instructors


class InstructorIn(BaseModel):
    name: str = Field(min_length=1)
    date_of_birth: date | None = None
    address: str | None = None
    phone: str | None = None
    skills: list[str] = []
    experience_at_joining: Decimal | None = Field(default=None, ge=0)
    courses: str | None = None
    certifications: str | None = None
    joining_date: date | None = None


class InstructorPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    date_of_birth: date | None = None
    address: str | None = None
    phone: str | None = None
    skills: list[str] | None = None
    experience_at_joining: Decimal | None = Field(default=None, ge=0)
    courses: str | None = None
    certifications: str | None = None
    joining_date: date | None = None


class InstructorOut(ORMModel):
    id: uuid.UUID
    name: str
    date_of_birth: date | None
    address: str | None
    phone: str | None
    skills: list[str]
    experience_at_joining: Decimal | None
    courses: str | None
    certifications: str | None
    joining_date: date | None
    age: int | None = None
    current_experience: Decimal | None = None
    created_at: datetime


# ---------------------------------------------------------------- locations & batches


class LocationIn(BaseModel):
    name: str = Field(min_length=1)
    code: str = Field(min_length=1)
    type: str | None = None
    address: str | None = None
    capacity_per_batch: int | None = Field(default=None, ge=0)
    parallel_batches: int | None = Field(default=None, ge=0)


class LocationPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    code: str | None = Field(default=None, min_length=1)
    type: str | None = None
    address: str | None = None
    capacity_per_batch: int | None = Field(default=None, ge=0)
    parallel_batches: int | None = Field(default=None, ge=0)


class LocationOut(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    type: str | None
    address: str | None
    capacity_per_batch: int | None
    parallel_batches: int | None
    created_at: datetime


class BatchIn(BaseModel):
    name: str = Field(min_length=1)
    code: str = Field(min_length=1)
    status: BatchStatus = BatchStatus.upcoming
    location_id: uuid.UUID
    instructor_id: uuid.UUID
    start_date: date | None = None
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    description: str | None = None


class BatchPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    code: str | None = Field(default=None, min_length=1)
    status: BatchStatus | None = None
    location_id: uuid.UUID | None = None
    instructor_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    description: str | None = None


class BatchOut(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    status: BatchStatus
    location_id: uuid.UUID
    instructor_id: uuid.UUID
    location_name: str | None = None
    instructor_name: str | None = None
    start_date: date | None
    end_date: date | None
    start_time: time | None
    end_time: time | None
    description: str | None
    enrolled_count: int = 0
    capacity: int | None = None
    created_at: datetime


# ---------------------------------------------------------------- enrollments


class EnrollmentIn(BaseModel):
    client_id: uuid.UUID
    batch_id: uuid.UUID
    start_date: date


class EnrollmentOut(ORMModel):
    id: uuid.UUID
    client_id: uuid.UUID
    batch_id: uuid.UUID
    client_name: str | None = None
    batch_name: str | None = None
    batch_code: str | None = None
    start_date: date
    capacity_warning: str | None = None
    created_at: datetime


# ---------------------------------------------------------------- subscriptions & invoices


class SubscriptionIn(BaseModel):
    service_id: uuid.UUID
    start_date: date
    discount_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class SubscriptionPatch(BaseModel):
    status: SubscriptionStatus


class SubscriptionOut(ORMModel):
    id: uuid.UUID
    client_id: uuid.UUID
    service_id: uuid.UUID
    client_name: str | None = None
    service_name: str | None = None
    billing_interval: BillingInterval | None = None
    rate: Decimal | None = None
    effective_rate: Decimal | None = None
    start_date: date
    discount_pct: Decimal
    status: SubscriptionStatus
    created_at: datetime


class InvoiceOut(ORMModel):
    id: uuid.UUID
    number: str
    client_id: uuid.UUID
    subscription_id: uuid.UUID
    client_name: str | None = None
    service_name: str | None = None
    period_label: str
    issue_date: date
    amount: Decimal
    status: InvoiceStatus
    overdue: bool = False
    created_at: datetime


class InvoicePage(Page[InvoiceOut]):
    outstanding_total: Decimal = Decimal("0")


class InvoicePatch(BaseModel):
    status: InvoiceStatus

    @field_validator("status")
    @classmethod
    def only_paid_or_void(cls, v: InvoiceStatus) -> InvoiceStatus:
        if v == InvoiceStatus.due:
            raise ValueError("status must be 'paid' or 'void'")
        return v


class GenerateMissingIn(BaseModel):
    client_id: uuid.UUID | None = None


class GenerateMissingOut(BaseModel):
    created: int


# ---------------------------------------------------------------- dashboard


class DashboardBatch(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    start_time: time | None
    end_time: time | None
    instructor_name: str | None
    location_name: str | None
    enrolled_count: int
    capacity: int | None


class DashboardOut(BaseModel):
    active_clients: int
    active_batches: int
    billed_this_month: Decimal
    overdue_count: int
    todays_batches: list[DashboardBatch]
    recent_enrollments: list[EnrollmentOut]
