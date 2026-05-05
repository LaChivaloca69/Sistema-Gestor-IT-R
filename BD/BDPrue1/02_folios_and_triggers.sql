/*
Folios por año (year-based counters) + triggers para autogenerar códigos:

- Asset: AST-YYYY-000001  (asset.asset_tag)
- Ticket: TCK-YYYY-000001 (ticket.code)
- Purchase Request: PR-YYYY-000001
- Purchase Order: PO-YYYY-000001
- Inventory Movement: MOV-YYYY-000001
- Maintenance Work Order: MNT-YYYY-000001
- Goods Receipt: GR-YYYY-000001

Cómo funciona:
- year_sequence guarda contador por (entity, year).
- next_year_seq incrementa atómicamente (con retry).
- make_year_code arma el string final.

Ventaja:
- No dependes de sequences globales.
- Cada año reinicia el contador.
*/

BEGIN;

CREATE TABLE IF NOT EXISTS year_sequence (
  entity text NOT NULL,
  year   int  NOT NULL,
  value  bigint NOT NULL DEFAULT 0,
  PRIMARY KEY (entity, year)
);

CREATE OR REPLACE FUNCTION next_year_seq(p_entity text, p_year int)
RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE v_next bigint;
BEGIN
  LOOP
    UPDATE year_sequence
      SET value = value + 1
      WHERE entity = p_entity AND year = p_year
      RETURNING value INTO v_next;

    IF FOUND THEN
      RETURN v_next;
    END IF;

    BEGIN
      INSERT INTO year_sequence(entity, year, value)
      VALUES (p_entity, p_year, 1)
      RETURNING value INTO v_next;
      RETURN v_next;
    EXCEPTION WHEN unique_violation THEN
      -- retry
    END;
  END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION make_year_code(p_prefix text, p_entity text, p_ts timestamptz, p_pad int DEFAULT 6)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  v_year int := EXTRACT(YEAR FROM p_ts)::int;
  v_seq  bigint := next_year_seq(p_entity, v_year);
BEGIN
  RETURN p_prefix || '-' || v_year::text || '-' || lpad(v_seq::text, p_pad, '0');
END;
$$;

-- ---- ASSET TAG ----
CREATE OR REPLACE FUNCTION trg_asset_set_tag()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  v_ts timestamptz := COALESCE(NEW.created_at, now());
BEGIN
  IF NEW.asset_tag IS NULL OR NEW.asset_tag = '' THEN
    NEW.asset_tag := make_year_code('AST', 'asset', v_ts, 6);
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS asset_set_tag ON asset;
CREATE TRIGGER asset_set_tag
BEFORE INSERT ON asset
FOR EACH ROW EXECUTE FUNCTION trg_asset_set_tag();

-- ---- TICKET CODE ----
CREATE OR REPLACE FUNCTION trg_ticket_set_code()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.code IS NULL OR NEW.code = '' THEN
    NEW.code := make_year_code('TCK', 'ticket', NEW.created_at, 6);
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS ticket_set_code ON ticket;
CREATE TRIGGER ticket_set_code
BEFORE INSERT ON ticket
FOR EACH ROW EXECUTE FUNCTION trg_ticket_set_code();

-- ---- PURCHASE REQUEST ----
CREATE OR REPLACE FUNCTION trg_pr_set_code()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.code IS NULL OR NEW.code = '' THEN
    NEW.code := make_year_code('PR', 'purchase_request', NEW.created_at, 6);
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS pr_set_code ON purchase_request;
CREATE TRIGGER pr_set_code
BEFORE INSERT ON purchase_request
FOR EACH ROW EXECUTE FUNCTION trg_pr_set_code();

-- ---- PURCHASE ORDER ----
CREATE OR REPLACE FUNCTION trg_po_set_code()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v_ts timestamptz := now();
BEGIN
  IF NEW.code IS NULL OR NEW.code = '' THEN
    NEW.code := make_year_code('PO', 'purchase_order', v_ts, 6);
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS po_set_code ON purchase_order;
CREATE TRIGGER po_set_code
BEFORE INSERT ON purchase_order
FOR EACH ROW EXECUTE FUNCTION trg_po_set_code();

-- ---- INVENTORY MOVEMENT ----
CREATE OR REPLACE FUNCTION trg_mov_set_code()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.code IS NULL OR NEW.code = '' THEN
    NEW.code := make_year_code('MOV', 'inventory_movement', NEW.movement_date, 6);
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS mov_set_code ON inventory_movement;
CREATE TRIGGER mov_set_code
BEFORE INSERT ON inventory_movement
FOR EACH ROW EXECUTE FUNCTION trg_mov_set_code();

-- ---- MAINTENANCE WORK ORDER ----
CREATE OR REPLACE FUNCTION trg_mwo_set_code()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.code IS NULL OR NEW.code = '' THEN
    NEW.code := make_year_code('MNT', 'maintenance_work_order', NEW.opened_at, 6);
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS mwo_set_code ON maintenance_work_order;
CREATE TRIGGER mwo_set_code
BEFORE INSERT ON maintenance_work_order
FOR EACH ROW EXECUTE FUNCTION trg_mwo_set_code();

-- ---- GOODS RECEIPT ----
CREATE OR REPLACE FUNCTION trg_gr_set_code()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.code IS NULL OR NEW.code = '' THEN
    NEW.code := make_year_code('GR', 'goods_receipt', COALESCE(NEW.received_at, now()), 6);
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS gr_set_code ON goods_receipt;
CREATE TRIGGER gr_set_code
BEFORE INSERT ON goods_receipt
FOR EACH ROW EXECUTE FUNCTION trg_gr_set_code();

COMMIT;