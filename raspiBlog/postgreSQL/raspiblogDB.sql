-- Database: raspiblog

-- DROP DATABASE IF EXISTS raspiblog;

CREATE DATABASE raspiblog
    WITH
    OWNER = raspiblog
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

ALTER DATABASE raspiblog
    SET "TimeZone" TO 'Europe/Amsterdam';

-- Role: raspiblog
-- DROP ROLE IF EXISTS raspiblog;

CREATE ROLE raspiblog WITH
  LOGIN
  SUPERUSER
  INHERIT
  CREATEDB
  CREATEROLE
  REPLICATION
  BYPASSRLS
  PASSWORD 'YOUR_PASSWORD_HERE';

CREATE SEQUENCE IF NOT EXISTS public.rb_runs_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

-- Table: public.rb_runs

DROP TABLE IF EXISTS public.rb_runs CASCADE;

CREATE TABLE IF NOT EXISTS public.rb_runs
(
    id integer NOT NULL DEFAULT nextval('rb_runs_id_seq'::regclass),
    start_datetime timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_datetime timestamp without time zone,
    status character varying(1) COLLATE pg_catalog."default",
    type character varying(2) COLLATE pg_catalog."default",
    CONSTRAINT rb_runs_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;

ALTER SEQUENCE public.rb_runs_id_seq
    OWNED BY public.rb_runs.id;

ALTER SEQUENCE public.rb_runs_id_seq
    OWNER TO raspiblog;

ALTER TABLE IF EXISTS public.rb_runs
    OWNER to raspiblog;

-- Table: public.rb_articles

DROP TABLE IF EXISTS public.rb_articles CASCADE;

CREATE SEQUENCE IF NOT EXISTS public.rb_articles_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 2147483647
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.rb_articles
(
    id integer NOT NULL DEFAULT nextval('rb_articles_id_seq'::regclass),
    run_id integer NOT NULL,
    url character varying(512) COLLATE pg_catalog."default" NOT NULL,
    topic character varying(512) COLLATE pg_catalog."default",
    summary text COLLATE pg_catalog."default",
    text character varying(50000) COLLATE pg_catalog."default",
    pub_date timestamp without time zone,
    title text COLLATE pg_catalog."default",
    status character varying(1) COLLATE pg_catalog."default",
    CONSTRAINT rb_articles_pkey PRIMARY KEY (id),
    CONSTRAINT rb_articles_url_pub_date_uk UNIQUE (url, pub_date)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.rb_articles
    OWNER to raspiblog;

ALTER SEQUENCE public.rb_articles_id_seq
    OWNED BY public.rb_articles.id;

ALTER SEQUENCE public.rb_articles_id_seq
    OWNER TO raspiblog;

-- View: public.rb_v_recent_articles

-- DROP VIEW public.rb_v_recent_articles;

CREATE OR REPLACE VIEW public.rb_v_recent_articles
 AS
 SELECT a.id,
    a.run_id,
    a.url,
    a.text,
    a.pub_date,
    a.title,
    r.start_datetime
   FROM rb_articles a
     JOIN rb_runs r ON a.run_id = r.id
  WHERE a.status IS NULL AND a.supply_channel::text = 'Nieuws'::text AND a.title !~~ 'Wekdienst%'::text AND date(a.pub_date) = CURRENT_DATE AND (a.url::text ~~ 'https://rtlnieuws.nl/nieuws/%'::text AND a.url::text !~~ 'https://rtlnieuws.nl/nieuws/sport/%'::text OR a.url::text ~~ 'https://nos.nl%'::text OR a.url::text ~~ 'https://www.omroepbrabant.nl%'::text)
  ORDER BY a.pub_date DESC;

ALTER TABLE public.rb_v_recent_articles
    OWNER TO raspiblog;

-- View: public.rb_v_sport_articles

-- DROP VIEW public.rb_v_sport_articles;

CREATE OR REPLACE VIEW public.rb_v_sport_articles
 AS
 SELECT a.id,
    a.run_id,
    a.url,
    a.text,
    a.pub_date,
    a.title,
    r.start_datetime
   FROM rb_articles a
     JOIN rb_runs r ON a.run_id = r.id
  WHERE (a.supply_channel::text = ANY (ARRAY['Voetbal'::character varying::text, 'Sport'::character varying::text, 'Wielrennen'::character varying::text, 'Schaatsen'::character varying::text])) AND date(a.pub_date) >= (CURRENT_DATE - 1) AND date(a.pub_date) <= CURRENT_DATE
  ORDER BY a.pub_date DESC;

ALTER TABLE public.rb_v_sport_articles
    OWNER TO raspiblog;

-- View: public.rb_v_entertainment_articles

-- DROP VIEW public.rb_v_entertainment_articles;

CREATE OR REPLACE VIEW public.rb_v_entertainment_articles
 AS
 SELECT a.id,
    a.run_id,
    a.url,
    a.text,
    a.pub_date,
    a.title,
    r.start_datetime
   FROM rb_articles a
     JOIN rb_runs r ON a.run_id = r.id
  WHERE a.supply_channel::text = 'Entertainment'::text AND a.status IS NULL AND date(a.pub_date) >= (CURRENT_DATE - 1) AND date(a.pub_date) <= CURRENT_DATE
  ORDER BY a.pub_date DESC;

ALTER TABLE public.rb_v_entertainment_articles
    OWNER TO raspiblog;



CREATE OR REPLACE FUNCTION set_supply_channel()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.url LIKE 'https://rtlnieuws.nl/nieuws/sport%' THEN
        NEW.supply_channel := 'Sport';
    ELSIF NEW.url LIKE 'https://rtlnieuws.nl/nieuws/%' THEN
        NEW.supply_channel := 'Nieuws';
    ELSIF NEW.url LIKE 'https://rtlnieuws.nl/boulevard%' THEN
        NEW.supply_channel := 'Entertainment';
    ELSIF NEW.url LIKE 'https://www.omroepbrabant.nl%' THEN
        NEW.supply_channel := 'Nieuws';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_supply_channel()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.supply_channel IS NULL THEN
        IF NEW.url LIKE 'https://rtlnieuws.nl/nieuws/sport%' THEN
            NEW.supply_channel := 'Sport';
        ELSIF NEW.url LIKE 'https://rtlnieuws.nl/nieuws/%' THEN
            NEW.supply_channel := 'Nieuws';
        ELSIF NEW.url LIKE 'https://rtlnieuws.nl/boulevard%' THEN
            NEW.supply_channel := 'Entertainment';
        ELSIF NEW.url LIKE 'https://www.omroepbrabant.nl%' THEN
            NEW.supply_channel := 'Nieuws';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER trigger_set_supply_channel
BEFORE INSERT ON rb_articles
FOR EACH ROW
EXECUTE FUNCTION set_supply_channel();


UPDATE rb_articles
SET supply_channel = 
    CASE 
        WHEN url LIKE 'https://rtlnieuws.nl/nieuws/sport%' THEN 'Sport'
        WHEN url LIKE 'https://rtlnieuws.nl/nieuws/%' THEN 'Nieuws'
        WHEN url LIKE 'https://rtlnieuws.nl/boulevard%' THEN 'Entertainment'
        WHEN url LIKE 'https://www.omroepbrabant.nl%' THEN 'Nieuws'
        ELSE supply_channel  -- Laat de bestaande waarde staan als geen match
    END
WHERE supply_channel IS NULL;  -- Alleen rijen updaten waar supply_channel nog leeg is

UPDATE rb_articles
SET supply_channel = 
    CASE 
        WHEN url LIKE 'https://rtlnieuws.nl/nieuws/sport%' THEN 'Sport'
        WHEN url LIKE 'https://rtlnieuws.nl/nieuws/%' THEN 'Nieuws'
        WHEN url LIKE 'https://rtlnieuws.nl/boulevard%' THEN 'Entertainment'
        WHEN url LIKE 'https://www.omroepbrabant.nl%' THEN 'Nieuws'
        ELSE supply_channel  -- Laat de bestaande waarde staan als geen match
    END
WHERE supply_channel = 'TBD';


-- 
ALTER TABLE IF EXISTS public.rb_runs  ADD COLUMN action character varying(50);
ALTER TABLE IF EXISTS public.rb_runs  ADD COLUMN ai_provider character varying(15);