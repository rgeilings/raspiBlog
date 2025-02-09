--
-- PostgreSQL database dump
--

-- Dumped from database version 16.3 (Debian 16.3-1.pgdg120+1)
-- Dumped by pg_dump version 16.3 (Debian 16.3-1.pgdg120+1)

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
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: set_supply_channel(); Type: FUNCTION; Schema: public; Owner: raspiblog
--

CREATE FUNCTION public.set_supply_channel() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.url LIKE 'https://rtlnieuws.nl/nieuws/sport%' THEN
        NEW.supply_channel := 'Sport';
    ELSIF NEW.url LIKE 'https://rtlnieuws.nl/nieuws/%' THEN
        NEW.supply_channel := 'Nieuws';
    ELSIF NEW.url LIKE 'https://rtlnieuws.nl/boulevard%' THEN
        NEW.supply_channel := 'Entertainment';
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.set_supply_channel() OWNER TO raspiblog;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: rb_articles; Type: TABLE; Schema: public; Owner: raspiblog
--

CREATE TABLE public.rb_articles (
    id integer NOT NULL,
    run_id integer NOT NULL,
    supply_channel character varying(15),
    title text,
    url character varying(512),
    pub_date timestamp without time zone,
    status character varying(1),
    text character varying(50000),
    topic character varying(512),
    summary text
);


ALTER TABLE public.rb_articles OWNER TO raspiblog;

--
-- Name: rb_articles_id_seq; Type: SEQUENCE; Schema: public; Owner: raspiblog
--

CREATE SEQUENCE public.rb_articles_id_seq
    START WITH 6717
    INCREMENT BY 1
    NO MINVALUE
    MAXVALUE 2147483647
    CACHE 1;


ALTER SEQUENCE public.rb_articles_id_seq OWNER TO raspiblog;

--
-- Name: rb_articles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: raspiblog
--

ALTER SEQUENCE public.rb_articles_id_seq OWNED BY public.rb_articles.id;


--
-- Name: rb_runs; Type: TABLE; Schema: public; Owner: raspiblog
--

CREATE TABLE public.rb_runs (
    id integer NOT NULL,
    start_datetime timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    end_datetime timestamp without time zone,
    status character varying(1),
    type character varying(2),
    action character varying(50),
    ai_provider character varying(15)
);


ALTER TABLE public.rb_runs OWNER TO raspiblog;

--
-- Name: rb_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: raspiblog
--

CREATE SEQUENCE public.rb_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.rb_runs_id_seq OWNER TO raspiblog;

--
-- Name: rb_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: raspiblog
--

ALTER SEQUENCE public.rb_runs_id_seq OWNED BY public.rb_runs.id;


--
-- Name: rb_trends; Type: TABLE; Schema: public; Owner: raspiblog
--

CREATE TABLE public.rb_trends (
    id integer NOT NULL,
    run_id integer NOT NULL,
    trend_text character varying(50) NOT NULL
);


ALTER TABLE public.rb_trends OWNER TO raspiblog;

--
-- Name: rb_trends_id_seq; Type: SEQUENCE; Schema: public; Owner: raspiblog
--

CREATE SEQUENCE public.rb_trends_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.rb_trends_id_seq OWNER TO raspiblog;

--
-- Name: rb_trends_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: raspiblog
--

ALTER SEQUENCE public.rb_trends_id_seq OWNED BY public.rb_trends.id;


--
-- Name: rb_v_entertainment_articles; Type: VIEW; Schema: public; Owner: raspiblog
--

CREATE VIEW public.rb_v_entertainment_articles AS
 SELECT a.id,
    a.run_id,
    a.url,
    a.text,
    a.pub_date,
    a.title,
    r.start_datetime
   FROM (public.rb_articles a
     JOIN public.rb_runs r ON ((a.run_id = r.id)))
  WHERE (((a.supply_channel)::text = 'Entertainment'::text) AND (a.status IS NULL) AND (date(a.pub_date) = CURRENT_DATE))
  ORDER BY a.pub_date DESC;


ALTER VIEW public.rb_v_entertainment_articles OWNER TO raspiblog;

--
-- Name: rb_v_6_random_entertainment_articles; Type: VIEW; Schema: public; Owner: raspiblog
--

CREATE VIEW public.rb_v_6_random_entertainment_articles AS
 WITH rtl AS (
         SELECT rb_v_entertainment_articles.id,
            rb_v_entertainment_articles.title AS label,
            rb_v_entertainment_articles.url,
            rb_v_entertainment_articles.text AS summary
           FROM public.rb_v_entertainment_articles
          WHERE ((rb_v_entertainment_articles.url)::text ~~ 'https://rtlnieuws%'::text)
          ORDER BY (random())
         LIMIT 3
        ), nos AS (
         SELECT rb_v_entertainment_articles.id,
            rb_v_entertainment_articles.title AS label,
            rb_v_entertainment_articles.url,
            rb_v_entertainment_articles.text AS summary
           FROM public.rb_v_entertainment_articles
          WHERE ((rb_v_entertainment_articles.url)::text ~~ 'https://nos.nl%'::text)
          ORDER BY (random())
         LIMIT 3
        ), combined AS (
         SELECT rtl.id,
            rtl.label,
            rtl.url,
            rtl.summary
           FROM rtl
        UNION ALL
         SELECT nos.id,
            nos.label,
            nos.url,
            nos.summary
           FROM nos
        ), extra AS (
         SELECT rb_v_entertainment_articles.id,
            rb_v_entertainment_articles.title AS label,
            rb_v_entertainment_articles.url,
            rb_v_entertainment_articles.text AS summary
           FROM public.rb_v_entertainment_articles
          ORDER BY (random())
         LIMIT (6 - ( SELECT count(*) AS count
                   FROM combined))
        ), final_combined AS (
         SELECT combined.id,
            combined.label,
            combined.url,
            combined.summary
           FROM combined
        UNION ALL
         SELECT extra.id,
            extra.label,
            extra.url,
            extra.summary
           FROM extra
        )
 SELECT id,
    label,
    url,
    summary
   FROM final_combined
  ORDER BY (random())
 LIMIT 6;


ALTER VIEW public.rb_v_6_random_entertainment_articles OWNER TO raspiblog;

--
-- Name: rb_v_recent_articles; Type: VIEW; Schema: public; Owner: raspiblog
--

CREATE VIEW public.rb_v_recent_articles AS
 SELECT a.id,
    a.run_id,
    a.url,
    a.text,
    a.pub_date,
    a.title,
    r.start_datetime
   FROM (public.rb_articles a
     JOIN public.rb_runs r ON ((a.run_id = r.id)))
  WHERE ((a.status IS NULL) AND ((a.supply_channel)::text = 'Nieuws'::text) AND (a.title !~~ 'Wekdienst%'::text) AND (date(a.pub_date) = CURRENT_DATE) AND ((((a.url)::text ~~ 'https://rtlnieuws.nl/nieuws/%'::text) AND ((a.url)::text !~~ 'https://rtlnieuws.nl/nieuws/sport/%'::text)) OR ((a.url)::text ~~ 'https://nos.nl%'::text) OR ((a.url)::text ~~ 'https://www.omroepbrabant.nl%'::text)))
  ORDER BY a.pub_date DESC;


ALTER VIEW public.rb_v_recent_articles OWNER TO raspiblog;

--
-- Name: rb_v_6_random_recent_articles; Type: VIEW; Schema: public; Owner: raspiblog
--

CREATE VIEW public.rb_v_6_random_recent_articles AS
 WITH rtl AS (
         SELECT rb_v_recent_articles.id,
            rb_v_recent_articles.title AS label,
            rb_v_recent_articles.url,
            rb_v_recent_articles.text AS summary
           FROM public.rb_v_recent_articles
          WHERE ((rb_v_recent_articles.url)::text ~~ 'https://rtlnieuws%'::text)
          ORDER BY (random())
         LIMIT 2
        ), nos AS (
         SELECT rb_v_recent_articles.id,
            rb_v_recent_articles.title AS label,
            rb_v_recent_articles.url,
            rb_v_recent_articles.text AS summary
           FROM public.rb_v_recent_articles
          WHERE ((rb_v_recent_articles.url)::text ~~ 'https://nos.nl%'::text)
          ORDER BY (random())
         LIMIT 2
        ), omroepbrabant AS (
         SELECT rb_v_recent_articles.id,
            rb_v_recent_articles.title AS label,
            rb_v_recent_articles.url,
            rb_v_recent_articles.text AS summary
           FROM public.rb_v_recent_articles
          WHERE ((rb_v_recent_articles.url)::text ~~ 'https://www.omroepbrabant.nl%'::text)
          ORDER BY (random())
         LIMIT 2
        ), combined AS (
         SELECT rtl.id,
            rtl.label,
            rtl.url,
            rtl.summary
           FROM rtl
        UNION ALL
         SELECT nos.id,
            nos.label,
            nos.url,
            nos.summary
           FROM nos
        UNION ALL
         SELECT omroepbrabant.id,
            omroepbrabant.label,
            omroepbrabant.url,
            omroepbrabant.summary
           FROM omroepbrabant
        ), extra AS (
         SELECT rb_v_recent_articles.id,
            rb_v_recent_articles.title AS label,
            rb_v_recent_articles.url,
            rb_v_recent_articles.text AS summary
           FROM public.rb_v_recent_articles
          ORDER BY (random())
         LIMIT (6 - ( SELECT count(*) AS count
                   FROM combined))
        ), final_combined AS (
         SELECT combined.id,
            combined.label,
            combined.url,
            combined.summary
           FROM combined
        UNION ALL
         SELECT extra.id,
            extra.label,
            extra.url,
            extra.summary
           FROM extra
        )
 SELECT id,
    label,
    url,
    summary
   FROM final_combined
  ORDER BY (random())
 LIMIT 6;


ALTER VIEW public.rb_v_6_random_recent_articles OWNER TO raspiblog;

--
-- Name: rb_v_sport_articles; Type: VIEW; Schema: public; Owner: raspiblog
--

CREATE VIEW public.rb_v_sport_articles AS
 SELECT a.id,
    a.run_id,
    a.url,
    a.text,
    a.pub_date,
    a.title,
    r.start_datetime
   FROM (public.rb_articles a
     JOIN public.rb_runs r ON ((a.run_id = r.id)))
  WHERE (((a.supply_channel)::text = ANY (ARRAY[('Voetbal'::character varying)::text, ('Sport'::character varying)::text, ('Wielrennen'::character varying)::text, ('Schaatsen'::character varying)::text])) AND (date(a.pub_date) = CURRENT_DATE))
  ORDER BY a.pub_date DESC;


ALTER VIEW public.rb_v_sport_articles OWNER TO raspiblog;

--
-- Name: rb_v_6_random_sport_articles; Type: VIEW; Schema: public; Owner: raspiblog
--

CREATE VIEW public.rb_v_6_random_sport_articles AS
 WITH rtl AS (
         SELECT rb_v_sport_articles.id,
            rb_v_sport_articles.title AS label,
            rb_v_sport_articles.url,
            rb_v_sport_articles.text AS summary
           FROM public.rb_v_sport_articles
          WHERE ((rb_v_sport_articles.url)::text ~~ 'https://rtlnieuws%'::text)
          ORDER BY (random())
         LIMIT 2
        ), nos AS (
         SELECT rb_v_sport_articles.id,
            rb_v_sport_articles.title AS label,
            rb_v_sport_articles.url,
            rb_v_sport_articles.text AS summary
           FROM public.rb_v_sport_articles
          WHERE ((rb_v_sport_articles.url)::text ~~ 'https://nos.nl%'::text)
          ORDER BY (random())
         LIMIT 2
        ), omroepbrabant AS (
         SELECT rb_v_sport_articles.id,
            rb_v_sport_articles.title AS label,
            rb_v_sport_articles.url,
            rb_v_sport_articles.text AS summary
           FROM public.rb_v_sport_articles
          WHERE ((rb_v_sport_articles.url)::text ~~ 'https://www.omroepbrabant.nl%'::text)
          ORDER BY (random())
         LIMIT 2
        ), combined AS (
         SELECT rtl.id,
            rtl.label,
            rtl.url,
            rtl.summary
           FROM rtl
        UNION ALL
         SELECT nos.id,
            nos.label,
            nos.url,
            nos.summary
           FROM nos
        UNION ALL
         SELECT omroepbrabant.id,
            omroepbrabant.label,
            omroepbrabant.url,
            omroepbrabant.summary
           FROM omroepbrabant
        ), extra AS (
         SELECT rb_v_sport_articles.id,
            rb_v_sport_articles.title AS label,
            rb_v_sport_articles.url,
            rb_v_sport_articles.text AS summary
           FROM public.rb_v_sport_articles
          ORDER BY (random())
         LIMIT (6 - ( SELECT count(*) AS count
                   FROM combined))
        ), final_combined AS (
         SELECT combined.id,
            combined.label,
            combined.url,
            combined.summary
           FROM combined
        UNION ALL
         SELECT extra.id,
            extra.label,
            extra.url,
            extra.summary
           FROM extra
        )
 SELECT id,
    label,
    url,
    summary
   FROM final_combined
  ORDER BY (random())
 LIMIT 6;


ALTER VIEW public.rb_v_6_random_sport_articles OWNER TO raspiblog;

--
-- Name: rb_v_duration; Type: VIEW; Schema: public; Owner: raspiblog
--

CREATE VIEW public.rb_v_duration AS
 SELECT action,
    start_datetime,
    end_datetime,
    age(end_datetime, start_datetime) AS duration,
    ai_provider
   FROM public.rb_runs
  WHERE (action IS NOT NULL)
  ORDER BY start_datetime DESC;


ALTER VIEW public.rb_v_duration OWNER TO raspiblog;

--
-- Name: rb_v_maakblog_dur; Type: VIEW; Schema: public; Owner: raspiblog
--

CREATE VIEW public.rb_v_maakblog_dur AS
 SELECT action,
    start_datetime,
    end_datetime,
    duration,
    ai_provider
   FROM public.rb_v_duration
  WHERE ((action)::text ~~ 'maak%'::text);


ALTER VIEW public.rb_v_maakblog_dur OWNER TO raspiblog;

--
-- Name: rb_articles id; Type: DEFAULT; Schema: public; Owner: raspiblog
--

ALTER TABLE ONLY public.rb_articles ALTER COLUMN id SET DEFAULT nextval('public.rb_articles_id_seq'::regclass);


--
-- Name: rb_runs id; Type: DEFAULT; Schema: public; Owner: raspiblog
--

ALTER TABLE ONLY public.rb_runs ALTER COLUMN id SET DEFAULT nextval('public.rb_runs_id_seq'::regclass);


--
-- Name: rb_trends id; Type: DEFAULT; Schema: public; Owner: raspiblog
--

ALTER TABLE ONLY public.rb_trends ALTER COLUMN id SET DEFAULT nextval('public.rb_trends_id_seq'::regclass);


--
-- Name: rb_articles rb_articles_pkey; Type: CONSTRAINT; Schema: public; Owner: raspiblog
--

ALTER TABLE ONLY public.rb_articles
    ADD CONSTRAINT rb_articles_pkey PRIMARY KEY (id);


--
-- Name: rb_runs rb_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: raspiblog
--

ALTER TABLE ONLY public.rb_runs
    ADD CONSTRAINT rb_runs_pkey PRIMARY KEY (id);


--
-- Name: rb_trends rb_trends_pkey; Type: CONSTRAINT; Schema: public; Owner: raspiblog
--

ALTER TABLE ONLY public.rb_trends
    ADD CONSTRAINT rb_trends_pkey PRIMARY KEY (id);


--
-- Name: unique_rtlnieuws_id; Type: INDEX; Schema: public; Owner: raspiblog
--

CREATE UNIQUE INDEX unique_rtlnieuws_id ON public.rb_articles USING btree ("substring"((url)::text, '/(\d{5,10})/'::text)) WHERE ((url)::text ~~ 'https://rtlnieuws.nl%'::text);


--
-- Name: rb_articles trigger_set_supply_channel; Type: TRIGGER; Schema: public; Owner: raspiblog
--

CREATE TRIGGER trigger_set_supply_channel BEFORE INSERT ON public.rb_articles FOR EACH ROW EXECUTE FUNCTION public.set_supply_channel();


--
-- Name: rb_articles fk_run_id; Type: FK CONSTRAINT; Schema: public; Owner: raspiblog
--

ALTER TABLE ONLY public.rb_articles
    ADD CONSTRAINT fk_run_id FOREIGN KEY (run_id) REFERENCES public.rb_runs(id) ON DELETE CASCADE;


--
-- Name: rb_trends rb_trends_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: raspiblog
--

ALTER TABLE ONLY public.rb_trends
    ADD CONSTRAINT rb_trends_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.rb_runs(id);


--
-- PostgreSQL database dump complete
--

