import enum
import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

JSONVariant = sa.JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


def str_enum(e: type[enum.Enum], name: str) -> sa.Enum:
    return sa.Enum(
        e,
        name=name,
        native_enum=False,
        length=30,
        validate_strings=True,
        values_callable=lambda x: [m.value for m in x],
    )


class Role(enum.StrEnum):
    superadmin = "superadmin"
    admin = "admin"
    staff = "staff"


class ServiceType(enum.StrEnum):
    subscription = "Subscription"
    usage_based = "Usage Based"
    one_time = "One Time"
    project_based = "Project Based"


class DeliveryMode(enum.StrEnum):
    offline = "Offline"
    online = "Online"
    hybrid = "Hybrid"
    self_service = "Self Service"


class BillingInterval(enum.StrEnum):
    na = "N/A"
    monthly = "Monthly"
    weekly = "Weekly"
    quarterly = "Quarterly"
    semi_annual = "Semi-Annual"
    annual = "Annual"


class CancellationPolicy(enum.StrEnum):
    non_refundable = "Non-Refundable"
    flexible = "Flexible"
    moderate = "Moderate"
    strict = "Strict"


class Gender(enum.StrEnum):
    female = "Female"
    male = "Male"
    non_binary = "Non-binary"
    prefer_not_to_say = "Prefer not to say"


class LifecycleStage(enum.StrEnum):
    lead = "Lead"
    prospect = "Prospect"
    customer = "Customer"
    lapsed = "Lapsed"


class AccountType(enum.StrEnum):
    individual = "Individual"
    corporate = "Corporate"
    family = "Family"


class SubscriptionStatus(enum.StrEnum):
    active = "active"
    ended = "ended"


class InvoiceStatus(enum.StrEnum):
    due = "due"
    paid = "paid"
    void = "void"


class BatchStatus(enum.StrEnum):
    active = "active"
    inactive = "inactive"
    upcoming = "upcoming"
    completed = "completed"


class CapacityPolicy(enum.StrEnum):
    warn = "warn"
    block = "block"


class PricingMode(enum.StrEnum):
    """How to read ServicePricingOption.value (§3.7).

    fixed_rate   — value IS the amount billed, ignoring service.rate
    discount_pct — value is a percentage off service.rate
    """

    fixed_rate = "fixed_rate"
    discount_pct = "discount_pct"


class TimestampMixin:
    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SubscriptionPlan(TimestampMixin, Base):
    __tablename__ = "subscription_plan"
    __table_args__ = (
        Index("subscription_plan_name_ci_key", sa.func.lower(sa.text("name")), unique=True),
    )

    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2), nullable=False)
    no_of_days: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text)


class Organisation(TimestampMixin, Base):
    __tablename__ = "organisation"

    name: Mapped[str] = mapped_column(sa.Text, unique=True, nullable=False)
    code: Mapped[str] = mapped_column(sa.Text, unique=True, nullable=False)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscription_plan.id", ondelete="RESTRICT")
    )
    subscription_starts_on: Mapped[date | None] = mapped_column(sa.Date)
    subscription_ends_on: Mapped[date | None] = mapped_column(sa.Date)
    currency: Mapped[str] = mapped_column(sa.Text, default="INR", nullable=False)
    timezone: Mapped[str] = mapped_column(sa.Text, default="Asia/Kolkata", nullable=False)
    invoice_prefix: Mapped[str] = mapped_column(sa.Text, default="INV", nullable=False)
    # Billing identity printed on every invoice (§3.9). Real columns rather than
    # settings JSON: a tax invoice needs these to be queryable and explicit.
    address: Mapped[str | None] = mapped_column(sa.Text)
    billing_email: Mapped[str | None] = mapped_column(sa.Text)
    phone: Mapped[str | None] = mapped_column(sa.Text)
    gstin: Mapped[str | None] = mapped_column(sa.Text)
    invoice_grace_days: Mapped[int] = mapped_column(sa.Integer, default=7, nullable=False)
    capacity_policy: Mapped[CapacityPolicy] = mapped_column(
        str_enum(CapacityPolicy, "capacity_policy"), default=CapacityPolicy.warn, nullable=False
    )
    settings: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    next_invoice_seq: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)

    plan: Mapped[SubscriptionPlan | None] = relationship(lazy="joined")


class AppUser(TimestampMixin, Base):
    __tablename__ = "app_user"
    __table_args__ = (
        UniqueConstraint("org_id", "username", name="app_user_username_per_org"),
        Index(
            "app_user_platform_username_key",
            "username",
            unique=True,
            sqlite_where=sa.text("org_id IS NULL"),
            postgresql_where=sa.text("org_id IS NULL"),
        ),
        CheckConstraint(
            "org_id IS NOT NULL OR role = 'superadmin'",
            name="app_user_orgless_is_superadmin",
        ),
    )

    org_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organisation.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    username: Mapped[str] = mapped_column(sa.Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    role: Mapped[Role] = mapped_column(str_enum(Role, "user_role"), nullable=False)

    org: Mapped[Organisation | None] = relationship(lazy="joined")


class OrgMixin:
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisation.id", ondelete="RESTRICT"), nullable=False, index=True
    )


class ArchivedMixin:
    archived_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class PricingOption(TimestampMixin, OrgMixin, ArchivedMixin, Base):
    """Org-configurable pricing tier ("Corporate Plan", "Student", ...) — §3.7.

    The catalog is per-org and open-ended; services opt in via ServicePricingOption
    and set their own price for each.
    """

    __tablename__ = "pricing_option"
    __table_args__ = (UniqueConstraint("org_id", "name", name="pricing_option_name_per_org"),)

    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text)
    # Account types eligible for this option; empty list means "anyone".
    applies_to: Mapped[list[str]] = mapped_column(JSONVariant, default=list, nullable=False)
    sort_order: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)


class Service(TimestampMixin, OrgMixin, ArchivedMixin, Base):
    __tablename__ = "service"
    __table_args__ = (UniqueConstraint("org_id", "sku", name="service_sku_per_org"),)

    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    sku: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text)
    service_type: Mapped[ServiceType] = mapped_column(
        str_enum(ServiceType, "service_type"), nullable=False
    )
    delivery_mode: Mapped[DeliveryMode] = mapped_column(
        str_enum(DeliveryMode, "delivery_mode"), nullable=False
    )
    max_capacity: Mapped[int | None] = mapped_column(sa.Integer)
    billing_interval: Mapped[BillingInterval] = mapped_column(
        str_enum(BillingInterval, "billing_interval"),
        default=BillingInterval.na,
        nullable=False,
    )
    rate: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2), nullable=False)
    cancellation_policy: Mapped[CancellationPolicy] = mapped_column(
        str_enum(CancellationPolicy, "cancellation_policy"),
        default=CancellationPolicy.flexible,
        nullable=False,
    )
    pricing_options: Mapped[list["ServicePricingOption"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ServicePricingOption.created_at",
    )

    deliverables: Mapped[list["ServiceDeliverable"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ServiceDeliverable.created_at"
    )


class ServiceDeliverable(TimestampMixin, Base):
    __tablename__ = "service_deliverable"

    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    quantity: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    unit: Mapped[str] = mapped_column(sa.Text, nullable=False)


class ServicePricingOption(TimestampMixin, Base):
    """What one service charges under one pricing option (§3.7).

    Child of service — no org_id; tenancy walks up through the parent, as with
    ServiceDeliverable. RESTRICT on the option keeps an in-use tier from vanishing.
    """

    __tablename__ = "service_pricing_option"
    __table_args__ = (
        UniqueConstraint("service_id", "pricing_option_id", name="service_pricing_option_once"),
    )

    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pricing_option_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pricing_option.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    pricing_mode: Mapped[PricingMode] = mapped_column(
        str_enum(PricingMode, "pricing_mode"), nullable=False
    )
    value: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2), nullable=False)

    option: Mapped[PricingOption] = relationship(lazy="joined")


class Client(TimestampMixin, OrgMixin, ArchivedMixin, Base):
    __tablename__ = "client"

    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    name_hint: Mapped[str | None] = mapped_column(sa.Text)
    phone: Mapped[str | None] = mapped_column(sa.Text)
    email: Mapped[str | None] = mapped_column(sa.Text)
    gender: Mapped[Gender | None] = mapped_column(str_enum(Gender, "gender"))
    date_of_birth: Mapped[date | None] = mapped_column(sa.Date)
    joining_date: Mapped[date | None] = mapped_column(sa.Date)
    lead_source: Mapped[str | None] = mapped_column(sa.Text)
    lifecycle_stage: Mapped[LifecycleStage] = mapped_column(
        str_enum(LifecycleStage, "lifecycle_stage"),
        default=LifecycleStage.lead,
        nullable=False,
    )
    do_not_contact: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    do_not_email: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    do_not_call: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    address: Mapped[str | None] = mapped_column(sa.Text)
    work: Mapped[str | None] = mapped_column(sa.Text)
    description: Mapped[str | None] = mapped_column(sa.Text)
    account_type: Mapped[AccountType] = mapped_column(
        str_enum(AccountType, "account_type"), default=AccountType.individual, nullable=False
    )
    company_name: Mapped[str | None] = mapped_column(sa.Text)
    gstin: Mapped[str | None] = mapped_column(sa.Text)
    company_contact: Mapped[str | None] = mapped_column(sa.Text)
    family_link_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("client.id", ondelete="SET NULL")
    )


class ContactNote(TimestampMixin, Base):
    __tablename__ = "contact_note"

    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    channel: Mapped[str] = mapped_column(sa.Text, nullable=False)
    text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )

    author: Mapped[AppUser] = relationship(lazy="joined")


class Instructor(TimestampMixin, OrgMixin, ArchivedMixin, Base):
    __tablename__ = "instructor"

    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(sa.Date)
    address: Mapped[str | None] = mapped_column(sa.Text)
    phone: Mapped[str | None] = mapped_column(sa.Text)
    skills: Mapped[list[str]] = mapped_column(JSONVariant, default=list, nullable=False)
    experience_at_joining: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 1))
    courses: Mapped[str | None] = mapped_column(sa.Text)
    certifications: Mapped[str | None] = mapped_column(sa.Text)
    joining_date: Mapped[date | None] = mapped_column(sa.Date)


class Location(TimestampMixin, OrgMixin, ArchivedMixin, Base):
    __tablename__ = "location"
    __table_args__ = (UniqueConstraint("org_id", "code", name="location_code_per_org"),)

    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    code: Mapped[str] = mapped_column(sa.Text, nullable=False)
    type: Mapped[str | None] = mapped_column(sa.Text)
    address: Mapped[str | None] = mapped_column(sa.Text)
    capacity_per_batch: Mapped[int | None] = mapped_column(sa.Integer)
    parallel_batches: Mapped[int | None] = mapped_column(sa.Integer)


# Which services a batch delivers (§5.5). A client may enrol only if they hold an active
# subscription to one of these; a batch with no linked service stays open to anyone.
batch_service = sa.Table(
    "batch_service",
    Base.metadata,
    sa.Column(
        "batch_id", sa.Uuid, sa.ForeignKey("batch.id", ondelete="CASCADE"), primary_key=True
    ),
    sa.Column(
        "service_id", sa.Uuid, sa.ForeignKey("service.id", ondelete="CASCADE"), primary_key=True
    ),
)


class Batch(TimestampMixin, OrgMixin, ArchivedMixin, Base):
    __tablename__ = "batch"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="batch_code_per_org"),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="batch_dates_ordered",
        ),
    )

    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    code: Mapped[str] = mapped_column(sa.Text, nullable=False)
    status: Mapped[BatchStatus] = mapped_column(
        str_enum(BatchStatus, "batch_status"), default=BatchStatus.upcoming, nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("location.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    instructor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instructor.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    start_date: Mapped[date | None] = mapped_column(sa.Date)
    end_date: Mapped[date | None] = mapped_column(sa.Date)
    start_time: Mapped[time | None] = mapped_column(sa.Time)
    end_time: Mapped[time | None] = mapped_column(sa.Time)
    description: Mapped[str | None] = mapped_column(sa.Text)

    location: Mapped[Location] = relationship(lazy="joined")
    instructor: Mapped[Instructor] = relationship(lazy="joined")
    services: Mapped[list["Service"]] = relationship(
        secondary=batch_service, lazy="selectin", order_by="Service.name"
    )


class Enrollment(TimestampMixin, Base):
    __tablename__ = "enrollment"
    __table_args__ = (
        UniqueConstraint("batch_id", "client_id", name="enrollment_once_per_batch"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("batch.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(sa.Date, nullable=False)

    client: Mapped[Client] = relationship(lazy="joined")
    batch: Mapped[Batch] = relationship(lazy="joined")


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscription"

    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    # Null means base rate. When set, the option's price wins outright and
    # discount_pct is forced to 0 on write (§3.7) — never a stored-but-ignored value.
    pricing_option_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pricing_option.id", ondelete="RESTRICT"), index=True
    )
    discount_pct: Mapped[Decimal] = mapped_column(
        sa.Numeric(5, 2), default=Decimal("0"), nullable=False
    )
    # Signed carry from payment differences (§3.8): positive means the client underpaid
    # and owes it on the next invoice; negative is a credit that reduces the next one.
    # Consumed at generation; a credit larger than one invoice rolls forward.
    carry_balance: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        str_enum(SubscriptionStatus, "subscription_status"),
        default=SubscriptionStatus.active,
        nullable=False,
    )

    client: Mapped[Client] = relationship(lazy="joined")
    service: Mapped[Service] = relationship(lazy="joined")
    pricing_option: Mapped[PricingOption | None] = relationship(lazy="joined")


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoice"
    # Keyed on period_start, not period_label: once end dates are editable a label like
    # "Jul 2026" can legitimately describe two different periods (§3.8).
    #
    # Partial, excluding void: a voided invoice is ignored by generation, so its period
    # is re-billed — and the replacement has to be able to sit alongside the voided row.
    # Live invoices are still one-per-period, which is what idempotency rests on.
    __table_args__ = (
        sa.Index(
            "invoice_one_per_period",
            "subscription_id",
            "period_start",
            unique=True,
            postgresql_where=sa.text("status <> 'void'"),
            sqlite_where=sa.text("status <> 'void'"),
        ),
    )

    number: Mapped[str] = mapped_column(sa.Text, nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscription.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    period_label: Mapped[str] = mapped_column(sa.Text, nullable=False)
    period_start: Mapped[date] = mapped_column(sa.Date, nullable=False)
    period_end: Mapped[date] = mapped_column(sa.Date, nullable=False)
    # Set when a human edits period_end. Generation re-anchors from the latest adjusted
    # invoice, so an extension shifts every later period instead of being swallowed.
    period_end_adjusted: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, nullable=False
    )
    issue_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2), nullable=False)
    # What was actually received, set when the invoice is marked paid. May differ from
    # amount when a payment is settled short/over or the difference is carried forward.
    paid_amount: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 2))
    # True only when a payment difference was carried onto the subscription's next
    # invoice (not settled). Lets the listing surface the still-consequential ones.
    difference_carried: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, nullable=False
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        str_enum(InvoiceStatus, "invoice_status"), default=InvoiceStatus.due, nullable=False
    )

    client: Mapped[Client] = relationship(lazy="joined")
    subscription: Mapped[Subscription] = relationship(lazy="joined")
