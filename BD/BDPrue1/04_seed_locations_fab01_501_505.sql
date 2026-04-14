/*
Seed de ubicaciones para la fábrica.

Crea:
- site: FAB-01 (si no existe)
- edificios: 501..505 (location_type=building)
- dentro de cada edificio:
  - Piso 1  : <B>-P1   (zone)
  - Piso 2  : <B>-P2   (zone)
  - Oficinas: <B>-OF   (office)
  - Almacen : <B>-ALM  (warehouse)
  - Produccion: <B>-PROD (line)

Ejemplo:
  501
    501-P1
    501-P2
    501-OF
    501-ALM
    501-PROD
*/

BEGIN;

-- 1) Sede principal
INSERT INTO site (name, code, active)
VALUES ('Fabrica Principal', 'FAB-01', true)
ON CONFLICT (code) DO NOTHING;

-- 2) Insertar edificios 501-505
WITH s AS (
  SELECT id FROM site WHERE code = 'FAB-01'
),
buildings AS (
  SELECT * FROM (VALUES ('501'),('502'),('503'),('504'),('505')) AS b(code)
)
INSERT INTO location (site_id, name, code, location_type, parent_location_id, active)
SELECT
  s.id,
  'EDIFICIO ' || b.code AS name,
  b.code AS code,
  'building'::location_type,
  NULL,
  true
FROM s
JOIN buildings b ON true
ON CONFLICT (site_id, code) DO NOTHING;

-- 3) Insertar áreas estándar dentro de cada edificio
WITH s AS (
  SELECT id FROM site WHERE code = 'FAB-01'
),
b AS (
  SELECT l.id AS building_id, l.site_id, l.code AS building_code
  FROM location l
  JOIN s ON s.id = l.site_id
  WHERE l.location_type = 'building'::location_type
    AND l.code IN ('501','502','503','504','505')
),
areas AS (
  SELECT * FROM (VALUES
    ('P1',   'PISO 1',     'zone'::location_type),
    ('P2',   'PISO 2',     'zone'::location_type),
    ('OF',   'OFICINAS',   'office'::location_type),
    ('ALM',  'ALMACEN',    'warehouse'::location_type),
    ('PROD', 'PRODUCCION', 'line'::location_type)
  ) AS a(suffix, name, ltype)
)
INSERT INTO location (site_id, name, code, location_type, parent_location_id, active)
SELECT
  b.site_id,
  a.name || ' (EDIF ' || b.building_code || ')' AS name,
  b.building_code || '-' || a.suffix AS code,
  a.ltype,
  b.building_id,
  true
FROM b
CROSS JOIN areas a
ON CONFLICT (site_id, code) DO NOTHING;

COMMIT;