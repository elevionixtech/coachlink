import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    PricingMode,
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


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)

    @model_validator(mode="after")
    def _must_differ(self) -> "PasswordChangeIn":
        if self.current_password == self.new_password:
            raise ValueError("New password must differ from the current one")
        return self


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
    address: str | None = None
    billing_email: str | None = None
    phone: str | None = None
    gstin: str | None = None
    upi_id: str | None = None
    bank_account_name: str | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None
    bank_name: str | None = None
    show_payment_qr: bool = True
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
    address: str | None = None
    billing_email: str | None = None
    phone: str | None = None
    gstin: str | None = None
    upi_id: str | None = None
    bank_account_name: str | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None
    bank_name: str | None = None
    show_payment_qr: bool = True
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


# ---------------------------------------------------- pricing options (§3.7)


class PricingOptionIn(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    # Empty means any account type may use the option.
    applies_to: list[AccountType] = []
    sort_order: int = 0


class PricingOptionPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    applies_to: list[AccountType] | None = None
    sort_order: int | None = None


class PricingOptionOut(ORMModel):
    id: uuid.UUID
    name: str
    description: str | None
    applies_to: list[AccountType]
    sort_order: int
    created_at: datetime


class ServicePricingOptionIn(BaseModel):
    pricing_option_id: uuid.UUID
    pricing_mode: PricingMode
    value: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def _value_fits_mode(self) -> "ServicePricingOptionIn":
        # `value` is polymorphic, so the bound depends on the mode — one CHECK
        # constraint could not express this.
        if self.pricing_mode is PricingMode.discount_pct and self.value > 100:
            raise ValueError("A discount_pct value must be between 0 and 100")
        return self


class ServicePricingOptionOut(ORMModel):
    id: uuid.UUID
    pricing_option_id: uuid.UUID
    pricing_mode: PricingMode
    value: Decimal
    option_name: str | None = None
    # service.rate with this option applied — what a client on it actually pays.
    effective_rate: Decimal | None = None


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
    pricing_options: list[ServicePricingOptionIn] = []
    deliverables: list[DeliverableIn] = []

    @model_validator(mode="after")
    def _options_unique(self) -> "ServiceIn":
        ids = [p.pricing_option_id for p in self.pricing_options]
        if len(ids) != len(set(ids)):
            raise ValueError("A service may price each option only once")
        return self


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
    pricing_options: list[ServicePricingOptionIn] | None = None
    deliverables: list[DeliverableIn] | None = None

    @model_validator(mode="after")
    def _options_unique(self) -> "ServicePatch":
        ids = [p.pricing_option_id for p in self.pricing_options or []]
        if len(ids) != len(set(ids)):
            raise ValueError("A service may price each option only once")
        return self


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
    pricing_options: list[ServicePricingOptionOut]
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
    joining_date: date | None = None
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
    joining_date: date | None = None
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
    joining_date: date | None
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


class ServiceRef(ORMModel):
    id: uuid.UUID
    name: str
    sku: str


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
    # Services this batch delivers; empty leaves the batch open to any client (§5.5).
    service_ids: list[uuid.UUID] = []


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
    service_ids: list[uuid.UUID] | None = None


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
    services: list[ServiceRef] = []
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
    # When set, the option's price wins and discount_pct is forced to 0 (§3.7).
    pricing_option_id: uuid.UUID | None = None
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
    pricing_option_id: uuid.UUID | None = None
    pricing_option_name: str | None = None
    discount_pct: Decimal
    carry_balance: Decimal = Decimal("0")
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
    period_start: date
    period_end: date
    period_end_adjusted: bool = False
    issue_date: date
    amount: Decimal
    paid_amount: Decimal | None = None
    difference_carried: bool = False
    status: InvoiceStatus
    overdue: bool = False
    # True only for the newest live invoice of a subscription — the one PATCH will accept.
    can_adjust_period: bool = False
    # True while the subscription is active, so a payment difference has a next invoice
    # to carry to. When false, a mismatch must be settled.
    can_carry_forward: bool = False
    created_at: datetime


class InvoiceParty(BaseModel):
    """One side of the invoice header — issuer or bill-to."""

    name: str
    company_name: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    gstin: str | None = None


class PaymentInfo(BaseModel):
    """How a client can pay the invoice online (§3.9)."""

    upi_id: str | None = None
    bank_account_name: str | None = None
    bank_account_number: str | None = None
    bank_ifsc: str | None = None
    bank_name: str | None = None
    show_qr: bool = True

    def has_any(self) -> bool:
        return bool(self.upi_id or self.bank_account_number)


class InvoiceDocumentOut(InvoiceOut):
    """Everything a printable invoice needs, in one request."""

    currency: str
    billing_interval: BillingInterval | None = None
    service_description: str | None = None
    pricing_option_name: str | None = None
    issued_by: InvoiceParty
    bill_to: InvoiceParty
    payment: PaymentInfo = PaymentInfo()
    # Deliverables of the service, e.g. "12 classes — Hatha yoga classes".
    includes: list[str] = []


class InvoicePage(Page[InvoiceOut]):
    outstanding_total: Decimal = Decimal("0")


class InvoicePatch(BaseModel):
    status: InvoiceStatus | None = None
    # Moving a period's end shifts every later one (§3.8) — out to extend, in to close
    # early once a usage-based plan's deliverables are all delivered. period_start is
    # never editable: moving it would gap or overlap against the previous invoice.
    period_end: date | None = None
    # When marking paid: the amount actually received. If it differs from the invoice,
    # carry_forward decides whether the difference rides to the next invoice or the
    # invoice is simply settled at what was paid.
    paid_amount: Decimal | None = Field(default=None, ge=0)
    carry_forward: bool = False

    @field_validator("status")
    @classmethod
    def only_paid_or_void(cls, v: InvoiceStatus | None) -> InvoiceStatus | None:
        if v == InvoiceStatus.due:
            raise ValueError("status must be 'paid' or 'void'")
        return v

    @model_validator(mode="after")
    def _something_to_change(self) -> "InvoicePatch":
        if self.status is None and self.period_end is None:
            raise ValueError("Provide status or period_end")
        return self


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
