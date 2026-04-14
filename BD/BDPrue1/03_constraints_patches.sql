/*
Constraints de formato y "calidad de datos".

- location.code:
  * obligatorio (ya lo es)
  * sin espacios
  * solo A-Z, 0-9 y guiones
- asset.asset_tag: AST-YYYY-000001
- ticket.code: TCK-YYYY-000001
- PR/PO/MOV/MNT/GR códigos con formato fijo
- asset.serial_number: sin espacios (regex permisivo)
*/

BEGIN;

-- -------- location.code format (no spaces, only A-Z0-9 and '-') --------
UPDATE location
SET code = upper(replace(code, ' ', '-'))
WHERE code <> upper(code) OR position(' ' in code) > 0;

ALTER TABLE location
  DROP CONSTRAINT IF EXISTS chk_location_code_format;

ALTER TABLE location
  ADD CONSTRAINT chk_location_code_format
  CHECK (code ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$');

-- -------- normalize to uppercase (optional) --------
UPDATE asset SET asset_tag = upper(asset_tag) WHERE asset_tag IS NOT NULL AND asset_tag <> upper(asset_tag);
UPDATE ticket SET code = upper(code) WHERE code IS NOT NULL AND code <> upper(code);
UPDATE purchase_request SET code = upper(code) WHERE code IS NOT NULL AND code <> upper(code);
UPDATE purchase_order SET code = upper(code) WHERE code IS NOT NULL AND code <> upper(code);
UPDATE inventory_movement SET code = upper(code) WHERE code IS NOT NULL AND code <> upper(code);
UPDATE maintenance_work_order SET code = upper(code) WHERE code IS NOT NULL AND code <> upper(code);
UPDATE goods_receipt SET code = upper(code) WHERE code IS NOT NULL AND code <> upper(code);

-- -------- code format checks --------
ALTER TABLE asset DROP CONSTRAINT IF EXISTS chk_asset_tag_format;
ALTER TABLE asset ADD CONSTRAINT chk_asset_tag_format
  CHECK (asset_tag ~ '^AST-[0-9]{4}-[0-9]{6}$');

ALTER TABLE ticket DROP CONSTRAINT IF EXISTS chk_ticket_code_format;
ALTER TABLE ticket ADD CONSTRAINT chk_ticket_code_format
  CHECK (code ~ '^TCK-[0-9]{4}-[0-9]{6}$');

ALTER TABLE purchase_request DROP CONSTRAINT IF EXISTS chk_purchase_request_code_format;
ALTER TABLE purchase_request ADD CONSTRAINT chk_purchase_request_code_format
  CHECK (code ~ '^PR-[0-9]{4}-[0-9]{6}$');

ALTER TABLE purchase_order DROP CONSTRAINT IF EXISTS chk_purchase_order_code_format;
ALTER TABLE purchase_order ADD CONSTRAINT chk_purchase_order_code_format
  CHECK (code ~ '^PO-[0-9]{4}-[0-9]{6}$');

ALTER TABLE inventory_movement DROP CONSTRAINT IF EXISTS chk_inventory_movement_code_format;
ALTER TABLE inventory_movement ADD CONSTRAINT chk_inventory_movement_code_format
  CHECK (code ~ '^MOV-[0-9]{4}-[0-9]{6}$');

ALTER TABLE maintenance_work_order DROP CONSTRAINT IF EXISTS chk_maintenance_work_order_code_format;
ALTER TABLE maintenance_work_order ADD CONSTRAINT chk_maintenance_work_order_code_format
  CHECK (code ~ '^MNT-[0-9]{4}-[0-9]{6}$');

ALTER TABLE goods_receipt DROP CONSTRAINT IF EXISTS chk_goods_receipt_code_format;
ALTER TABLE goods_receipt ADD CONSTRAINT chk_goods_receipt_code_format
  CHECK (code ~ '^GR-[0-9]{4}-[0-9]{6}$');

-- -------- serial number: no spaces (permissive allowed chars) --------
UPDATE asset
SET serial_number = btrim(serial_number)
WHERE serial_number IS NOT NULL AND serial_number <> btrim(serial_number);

ALTER TABLE asset
  DROP CONSTRAINT IF EXISTS chk_asset_serial_no_spaces;

ALTER TABLE asset
  ADD CONSTRAINT chk_asset_serial_no_spaces
  CHECK (
    serial_number IS NULL
    OR serial_number ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{2,63}$'
  );

COMMIT;