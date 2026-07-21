--
-- PostgreSQL database dump
--

\restrict NNYFIccN3kUfJqbRKQpOQRKaHwJjSsXdcOnPhGofxPYZVkf66JGQ0YekxsX5qw1

-- Dumped from database version 16.14 (Homebrew)
-- Dumped by pg_dump version 16.14 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: app_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_user (
    org_id uuid,
    name text NOT NULL,
    username text NOT NULL,
    password_hash text NOT NULL,
    role character varying(30) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT app_user_orgless_is_superadmin CHECK (((org_id IS NOT NULL) OR ((role)::text = 'superadmin'::text)))
);


--
-- Name: batch; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.batch (
    name text NOT NULL,
    code text NOT NULL,
    status character varying(30) NOT NULL,
    location_id uuid NOT NULL,
    instructor_id uuid NOT NULL,
    start_date date,
    end_date date,
    start_time time without time zone,
    end_time time without time zone,
    description text,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    org_id uuid NOT NULL,
    archived_at timestamp with time zone,
    CONSTRAINT batch_dates_ordered CHECK (((end_date IS NULL) OR (start_date IS NULL) OR (end_date >= start_date)))
);


--
-- Name: client; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.client (
    name text NOT NULL,
    name_hint text,
    phone text,
    email text,
    gender character varying(30),
    date_of_birth date,
    lead_source text,
    lifecycle_stage character varying(30) NOT NULL,
    do_not_contact boolean NOT NULL,
    do_not_email boolean NOT NULL,
    do_not_call boolean NOT NULL,
    address text,
    work text,
    description text,
    account_type character varying(30) NOT NULL,
    company_name text,
    gstin text,
    company_contact text,
    family_link_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    org_id uuid NOT NULL,
    archived_at timestamp with time zone
);


--
-- Name: contact_note; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contact_note (
    client_id uuid NOT NULL,
    date date NOT NULL,
    channel text NOT NULL,
    text text NOT NULL,
    author_id uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: enrollment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enrollment (
    client_id uuid NOT NULL,
    batch_id uuid NOT NULL,
    start_date date NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: instructor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instructor (
    name text NOT NULL,
    date_of_birth date,
    address text,
    phone text,
    skills jsonb NOT NULL,
    experience_at_joining numeric(5,1),
    courses text,
    certifications text,
    joining_date date,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    org_id uuid NOT NULL,
    archived_at timestamp with time zone
);


--
-- Name: invoice; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice (
    number text NOT NULL,
    client_id uuid NOT NULL,
    subscription_id uuid NOT NULL,
    period_label text NOT NULL,
    issue_date date NOT NULL,
    amount numeric(12,2) NOT NULL,
    status character varying(30) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: location; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.location (
    name text NOT NULL,
    code text NOT NULL,
    type text,
    address text,
    capacity_per_batch integer,
    parallel_batches integer,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    org_id uuid NOT NULL,
    archived_at timestamp with time zone
);


--
-- Name: organisation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organisation (
    name text NOT NULL,
    code text NOT NULL,
    plan_id uuid,
    subscription_starts_on date,
    subscription_ends_on date,
    currency text NOT NULL,
    timezone text NOT NULL,
    invoice_prefix text NOT NULL,
    invoice_grace_days integer NOT NULL,
    capacity_policy character varying(30) NOT NULL,
    settings jsonb NOT NULL,
    next_invoice_seq integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: service; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.service (
    name text NOT NULL,
    sku text NOT NULL,
    description text,
    service_type character varying(30) NOT NULL,
    delivery_mode character varying(30) NOT NULL,
    max_capacity integer,
    billing_interval character varying(30) NOT NULL,
    rate numeric(12,2) NOT NULL,
    cancellation_policy character varying(30) NOT NULL,
    pricing_options jsonb NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    org_id uuid NOT NULL,
    archived_at timestamp with time zone
);


--
-- Name: service_deliverable; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.service_deliverable (
    service_id uuid NOT NULL,
    name text NOT NULL,
    quantity integer NOT NULL,
    unit text NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: subscription; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscription (
    client_id uuid NOT NULL,
    service_id uuid NOT NULL,
    start_date date NOT NULL,
    discount_pct numeric(5,2) NOT NULL,
    status character varying(30) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: subscription_plan; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscription_plan (
    name text NOT NULL,
    amount numeric(12,2) NOT NULL,
    no_of_days integer NOT NULL,
    description text,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: app_user app_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT app_user_pkey PRIMARY KEY (id);


--
-- Name: app_user app_user_username_per_org; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT app_user_username_per_org UNIQUE (org_id, username);


--
-- Name: batch batch_code_per_org; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch
    ADD CONSTRAINT batch_code_per_org UNIQUE (org_id, code);


--
-- Name: batch batch_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch
    ADD CONSTRAINT batch_pkey PRIMARY KEY (id);


--
-- Name: client client_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client
    ADD CONSTRAINT client_pkey PRIMARY KEY (id);


--
-- Name: contact_note contact_note_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_note
    ADD CONSTRAINT contact_note_pkey PRIMARY KEY (id);


--
-- Name: enrollment enrollment_once_per_batch; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollment
    ADD CONSTRAINT enrollment_once_per_batch UNIQUE (batch_id, client_id);


--
-- Name: enrollment enrollment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollment
    ADD CONSTRAINT enrollment_pkey PRIMARY KEY (id);


--
-- Name: instructor instructor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instructor
    ADD CONSTRAINT instructor_pkey PRIMARY KEY (id);


--
-- Name: invoice invoice_one_per_period; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_one_per_period UNIQUE (subscription_id, period_label);


--
-- Name: invoice invoice_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_pkey PRIMARY KEY (id);


--
-- Name: location location_code_per_org; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location
    ADD CONSTRAINT location_code_per_org UNIQUE (org_id, code);


--
-- Name: location location_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location
    ADD CONSTRAINT location_pkey PRIMARY KEY (id);


--
-- Name: organisation organisation_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisation
    ADD CONSTRAINT organisation_code_key UNIQUE (code);


--
-- Name: organisation organisation_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisation
    ADD CONSTRAINT organisation_name_key UNIQUE (name);


--
-- Name: organisation organisation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisation
    ADD CONSTRAINT organisation_pkey PRIMARY KEY (id);


--
-- Name: service_deliverable service_deliverable_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service_deliverable
    ADD CONSTRAINT service_deliverable_pkey PRIMARY KEY (id);


--
-- Name: service service_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service
    ADD CONSTRAINT service_pkey PRIMARY KEY (id);


--
-- Name: service service_sku_per_org; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service
    ADD CONSTRAINT service_sku_per_org UNIQUE (org_id, sku);


--
-- Name: subscription subscription_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT subscription_pkey PRIMARY KEY (id);


--
-- Name: subscription_plan subscription_plan_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_plan
    ADD CONSTRAINT subscription_plan_pkey PRIMARY KEY (id);


--
-- Name: app_user_platform_username_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX app_user_platform_username_key ON public.app_user USING btree (username) WHERE (org_id IS NULL);


--
-- Name: ix_app_user_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_app_user_org_id ON public.app_user USING btree (org_id);


--
-- Name: ix_batch_instructor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_batch_instructor_id ON public.batch USING btree (instructor_id);


--
-- Name: ix_batch_location_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_batch_location_id ON public.batch USING btree (location_id);


--
-- Name: ix_batch_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_batch_org_id ON public.batch USING btree (org_id);


--
-- Name: ix_client_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_client_org_id ON public.client USING btree (org_id);


--
-- Name: ix_contact_note_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contact_note_client_id ON public.contact_note USING btree (client_id);


--
-- Name: ix_enrollment_batch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enrollment_batch_id ON public.enrollment USING btree (batch_id);


--
-- Name: ix_enrollment_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enrollment_client_id ON public.enrollment USING btree (client_id);


--
-- Name: ix_instructor_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_instructor_org_id ON public.instructor USING btree (org_id);


--
-- Name: ix_invoice_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_client_id ON public.invoice USING btree (client_id);


--
-- Name: ix_invoice_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_number ON public.invoice USING btree (number);


--
-- Name: ix_invoice_subscription_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_invoice_subscription_id ON public.invoice USING btree (subscription_id);


--
-- Name: ix_location_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_location_org_id ON public.location USING btree (org_id);


--
-- Name: ix_service_deliverable_service_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_service_deliverable_service_id ON public.service_deliverable USING btree (service_id);


--
-- Name: ix_service_org_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_service_org_id ON public.service USING btree (org_id);


--
-- Name: ix_subscription_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subscription_client_id ON public.subscription USING btree (client_id);


--
-- Name: ix_subscription_service_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subscription_service_id ON public.subscription USING btree (service_id);


--
-- Name: subscription_plan_name_ci_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX subscription_plan_name_ci_key ON public.subscription_plan USING btree (lower(name));


--
-- Name: app_user app_user_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT app_user_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisation(id) ON DELETE RESTRICT;


--
-- Name: batch batch_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch
    ADD CONSTRAINT batch_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.instructor(id) ON DELETE RESTRICT;


--
-- Name: batch batch_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch
    ADD CONSTRAINT batch_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(id) ON DELETE RESTRICT;


--
-- Name: batch batch_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.batch
    ADD CONSTRAINT batch_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisation(id) ON DELETE RESTRICT;


--
-- Name: client client_family_link_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client
    ADD CONSTRAINT client_family_link_id_fkey FOREIGN KEY (family_link_id) REFERENCES public.client(id) ON DELETE SET NULL;


--
-- Name: client client_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client
    ADD CONSTRAINT client_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisation(id) ON DELETE RESTRICT;


--
-- Name: contact_note contact_note_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_note
    ADD CONSTRAINT contact_note_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.app_user(id) ON DELETE RESTRICT;


--
-- Name: contact_note contact_note_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contact_note
    ADD CONSTRAINT contact_note_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.client(id) ON DELETE CASCADE;


--
-- Name: enrollment enrollment_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollment
    ADD CONSTRAINT enrollment_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.batch(id) ON DELETE RESTRICT;


--
-- Name: enrollment enrollment_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollment
    ADD CONSTRAINT enrollment_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.client(id) ON DELETE RESTRICT;


--
-- Name: instructor instructor_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instructor
    ADD CONSTRAINT instructor_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisation(id) ON DELETE RESTRICT;


--
-- Name: invoice invoice_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.client(id) ON DELETE RESTRICT;


--
-- Name: invoice invoice_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice
    ADD CONSTRAINT invoice_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.subscription(id) ON DELETE RESTRICT;


--
-- Name: location location_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.location
    ADD CONSTRAINT location_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisation(id) ON DELETE RESTRICT;


--
-- Name: organisation organisation_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organisation
    ADD CONSTRAINT organisation_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.subscription_plan(id) ON DELETE RESTRICT;


--
-- Name: service_deliverable service_deliverable_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service_deliverable
    ADD CONSTRAINT service_deliverable_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.service(id) ON DELETE CASCADE;


--
-- Name: service service_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service
    ADD CONSTRAINT service_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organisation(id) ON DELETE RESTRICT;


--
-- Name: subscription subscription_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT subscription_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.client(id) ON DELETE RESTRICT;


--
-- Name: subscription subscription_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription
    ADD CONSTRAINT subscription_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.service(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict NNYFIccN3kUfJqbRKQpOQRKaHwJjSsXdcOnPhGofxPYZVkf66JGQ0YekxsX5qw1

