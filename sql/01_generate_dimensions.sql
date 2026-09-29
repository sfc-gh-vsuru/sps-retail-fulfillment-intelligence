/*
  SPS Retail AI — Master Data Generator
  Generates all shared dimensions, retailer-specific locations, items,
  and the 2-year weekly activity time series.
  
  Run this in Snowflake with: CALL SPS_RETAIL_AI.STAGING.GENERATE_ALL_DATA();
*/

CREATE OR REPLACE PROCEDURE SPS_RETAIL_AI.STAGING.GENERATE_ALL_DATA()
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS CALLER
AS
BEGIN

-- ================================================================
-- 1. LOCATIONS — 66 stores across 3 retailers + 3 online channels
-- ================================================================

TRUNCATE TABLE IF EXISTS SPS_RETAIL_AI.SHARED.LOCATION;

-- Foot Locker locations (21 including online)
INSERT INTO SPS_RETAIL_AI.SHARED.LOCATION
    (LOCATION_ID, RETAILER_ID, SPS_RETAILER_NAME_KEY, SPS_CUSTOMER_LOCATION_KEY,
     STORE_NUMBER, STORE_NAME, LOCATION_TYPE, ADDRESS, CITY, STATE, POSTAL_CODE,
     COUNTRY, SPS_COUNTRY_CODE, SPS_COUNTRY, SPS_LATITUDE, SPS_LONGITUDE,
     REGION, CLIMATE, BANNER, STORE_CLASSIFICATION, STORE_SIZE, OPEN_DATE, CURRENCY_CODE)
SELECT
    'FL_' || LPAD(seq::VARCHAR, 4, '0'),
    'FL', 'Foot Locker', 'FL_LOC_' || LPAD(seq::VARCHAR, 6, '0'),
    LPAD((1000+seq)::VARCHAR, 6, '0'),
    banner || ' #' || (1000+seq)::VARCHAR,
    loc_type, addr, city, st, zip, 'USA', 'US', 'USA', lat, lon,
    rgn, clim, banner, tier, sz,
    DATEADD('day', -UNIFORM(365, 7300, RANDOM()), '2024-01-01'::DATE), 'USD'
FROM (
  SELECT ROW_NUMBER() OVER (ORDER BY 1) AS seq, t.*
  FROM (
    VALUES
    ('Foot Locker','STORE','100 W 42nd St','New York','NY','10036',40.7566,-73.9867,'Northeast','Temperate','A-Tier','Large'),
    ('Foot Locker','STORE','900 N Michigan Ave','Chicago','IL','60611',41.8989,-87.6242,'Midwest','Continental','A-Tier','Large'),
    ('Foot Locker','STORE','3333 Bristol St','Costa Mesa','CA','92626',33.6846,-117.8862,'West','Mediterranean','A-Tier','Medium'),
    ('Foot Locker','STORE','6801 Hollywood Blvd','Los Angeles','CA','90028',34.1017,-118.3387,'West','Mediterranean','A-Tier','Large'),
    ('Foot Locker','STORE','3000 Peachtree Rd','Atlanta','GA','30305',33.8398,-84.3776,'Southeast','Subtropical','A-Tier','Large'),
    ('Foot Locker','STORE','8687 N Central Expy','Dallas','TX','75225',32.8664,-96.7704,'South','Subtropical','A-Tier','Medium'),
    ('Foot Locker','STORE','701 S Miami Ave','Miami','FL','33130',25.7658,-80.1936,'Southeast','Tropical','A-Tier','Medium'),
    ('Foot Locker','STORE','2100 Pennsylvania Ave','Washington','DC','20037',38.9028,-77.0485,'Northeast','Temperate','A-Tier','Medium'),
    ('Foot Locker','STORE','1301 2nd Ave','Seattle','WA','98101',47.6079,-122.3365,'Northwest','Maritime','A-Tier','Medium'),
    ('Foot Locker','STORE','7014 E Camelback Rd','Scottsdale','AZ','85251',33.5082,-111.9297,'Southwest','Arid','A-Tier','Medium'),
    ('Champs Sports','STORE','2301 NW Expy','Oklahoma City','OK','73112',35.5197,-97.5659,'South','Subtropical','B-Tier','Medium'),
    ('Champs Sports','STORE','1 Garden State Plz','Paramus','NJ','07652',40.9196,-74.0759,'Northeast','Temperate','B-Tier','Medium'),
    ('Champs Sports','STORE','8500 Beverly Blvd','Los Angeles','CA','90048',34.0763,-118.3735,'West','Mediterranean','B-Tier','Small'),
    ('Champs Sports','STORE','555 Mall Dr','San Rafael','CA','94903',38.0037,-122.5425,'West','Mediterranean','B-Tier','Small'),
    ('Kids Foot Locker','STORE','200 E Pratt St','Baltimore','MD','21202',39.2862,-76.6099,'Northeast','Temperate','B-Tier','Small'),
    ('Kids Foot Locker','STORE','400 Commons Way','Bridgewater','NJ','08807',40.5963,-74.6042,'Northeast','Temperate','B-Tier','Small'),
    ('WSS','STORE','5440 Whittier Blvd','East Los Angeles','CA','90022',34.0238,-118.1691,'West','Mediterranean','C-Tier','Large'),
    ('WSS','STORE','1450 Arden Way','Sacramento','CA','95815',38.6007,-121.4405,'West','Mediterranean','C-Tier','Medium'),
    ('Foot Locker','STORE','500 Baybrook Mall','Friendswood','TX','77546',29.5300,-95.1555,'South','Subtropical','B-Tier','Large'),
    ('Foot Locker','STORE','1065 Ave of Americas','New York','NY','10018',40.7537,-73.9841,'Northeast','Temperate','A-Tier','Medium'),
    ('Foot Locker','INTERNET','Online Fulfillment','Online','NA','00000',0.0,0.0,'National','N/A','Digital','N/A')
  AS t(banner, loc_type, addr, city, st, zip, lat, lon, rgn, clim, tier, sz)
  ) t
);

-- Bass Pro locations (20 including online)
INSERT INTO SPS_RETAIL_AI.SHARED.LOCATION
    (LOCATION_ID, RETAILER_ID, SPS_RETAILER_NAME_KEY, SPS_CUSTOMER_LOCATION_KEY,
     STORE_NUMBER, STORE_NAME, LOCATION_TYPE, ADDRESS, CITY, STATE, POSTAL_CODE,
     COUNTRY, SPS_COUNTRY_CODE, SPS_COUNTRY, SPS_LATITUDE, SPS_LONGITUDE,
     REGION, CLIMATE, BANNER, STORE_CLASSIFICATION, STORE_SIZE, OPEN_DATE, CURRENCY_CODE)
SELECT
    'BP_' || LPAD(seq::VARCHAR, 4, '0'),
    'BP', 'Bass Pro Shops', 'BP_LOC_' || LPAD(seq::VARCHAR, 6, '0'),
    LPAD((2000+seq)::VARCHAR, 6, '0'),
    banner || ' #' || (2000+seq)::VARCHAR,
    loc_type, addr, city, st, zip, 'USA', 'US', 'USA', lat, lon,
    rgn, clim, banner, 'Destination', sz,
    DATEADD('day', -UNIFORM(730, 10950, RANDOM()), '2024-01-01'::DATE), 'USD'
FROM (
  SELECT ROW_NUMBER() OVER (ORDER BY 1) AS seq, t.*
  FROM (
    VALUES
    ('Bass Pro Shops','STORE','1 Bass Pro Dr','Springfield','MO','65898',37.1885,-93.2913,'Midwest','Continental','Flagship'),
    ('Bass Pro Shops','STORE','5156 International Dr','Orlando','FL','32819',28.4608,-81.4646,'Southeast','Tropical','Large'),
    ('Bass Pro Shops','STORE','6140 Macon Rd','Memphis','TN','38134',35.1284,-89.8647,'South','Subtropical','Large'),
    ('Bass Pro Shops','STORE','700 Assembly Row','Somerville','MA','02145',42.3955,-71.0807,'Northeast','Temperate','Large'),
    ('Bass Pro Shops','STORE','7051 Cabela Dr','Gonzales','LA','70737',30.2394,-90.9149,'South','Subtropical','Medium'),
    ('Cabelas','STORE','12901 Cabela Dr','Sidney','NE','69162',41.1236,-102.9714,'Plains','Continental','Medium'),
    ('Cabelas','STORE','1 Cabela Dr','Hamburg','PA','19526',40.5575,-75.9775,'Northeast','Temperate','Large'),
    ('Bass Pro Shops','STORE','2500 Bass Pro Dr','Grapevine','TX','76051',32.9417,-97.0730,'South','Subtropical','Large'),
    ('Bass Pro Shops','STORE','3950 Barranca Pkwy','Irvine','CA','92606',33.6937,-117.7951,'West','Mediterranean','Medium'),
    ('Cabelas','STORE','200 Cabela Dr','Post Falls','ID','83854',47.7230,-116.9632,'Northwest','Continental','Medium'),
    ('Bass Pro Shops','STORE','600 Bass Pro Dr','Pearl','MS','39208',32.2729,-90.1107,'South','Subtropical','Medium'),
    ('Bass Pro Shops','STORE','1365 S 5th St','St Charles','MO','63301',38.7702,-90.4993,'Midwest','Continental','Large'),
    ('Bass Pro Shops','STORE','8901 J M Keynes Dr','Charlotte','NC','28262',35.3396,-80.7436,'Southeast','Subtropical','Medium'),
    ('Bass Pro Shops','STORE','10 Outdoor World Dr','Prattville','AL','36066',32.4684,-86.4238,'Southeast','Subtropical','Medium'),
    ('Bass Pro Shops','STORE','1 Bass Pro Mills Dr','Auburn Hills','MI','48326',42.7141,-83.2283,'Midwest','Continental','Large'),
    ('Cabelas','STORE','400 Cabela Dr','Allen','TX','75013',33.1275,-96.6459,'South','Subtropical','Large'),
    ('Bass Pro Shops','STORE','3001 Bass Pro Way','Clarksville','IN','47129',38.3128,-85.7565,'Midwest','Continental','Medium'),
    ('Cabelas','STORE','100 Cabela Blvd','Scarborough','ME','04074',43.5733,-70.3577,'Northeast','Temperate','Medium'),
    ('Bass Pro Shops','STORE','5001 Bass Pro Cir','Denham Springs','LA','70726',30.4515,-90.9406,'South','Subtropical','Medium'),
    ('Bass Pro Shops','INTERNET','Online','Online','NA','00000',0.0,0.0,'National','N/A','N/A','N/A')
  AS t(banner, loc_type, addr, city, st, zip, lat, lon, rgn, clim, sz)
  ) t
);

-- Urban Outfitters locations (21 including online)
INSERT INTO SPS_RETAIL_AI.SHARED.LOCATION
    (LOCATION_ID, RETAILER_ID, SPS_RETAILER_NAME_KEY, SPS_CUSTOMER_LOCATION_KEY,
     STORE_NUMBER, STORE_NAME, LOCATION_TYPE, ADDRESS, CITY, STATE, POSTAL_CODE,
     COUNTRY, SPS_COUNTRY_CODE, SPS_COUNTRY, SPS_LATITUDE, SPS_LONGITUDE,
     REGION, CLIMATE, BANNER, STORE_CLASSIFICATION, STORE_SIZE, OPEN_DATE, CURRENCY_CODE)
SELECT
    'UO_' || LPAD(seq::VARCHAR, 4, '0'),
    'UO', 'Urban Outfitters', 'UO_LOC_' || LPAD(seq::VARCHAR, 6, '0'),
    LPAD((3000+seq)::VARCHAR, 6, '0'),
    'Urban Outfitters #' || (3000+seq)::VARCHAR,
    loc_type, addr, city, st, zip, 'USA', 'US', 'USA', lat, lon,
    rgn, clim, 'Urban Outfitters', tier, sz,
    DATEADD('day', -UNIFORM(365, 5475, RANDOM()), '2024-01-01'::DATE), 'USD'
FROM (
  SELECT ROW_NUMBER() OVER (ORDER BY 1) AS seq, t.*
  FROM (
    VALUES
    ('STORE','1627 Walnut St','Philadelphia','PA','19103',39.9510,-75.1683,'Northeast','Temperate','Flagship','Large'),
    ('STORE','628 Broadway','New York','NY','10012',40.7263,-73.9960,'Northeast','Temperate','A-Tier','Large'),
    ('STORE','1333 M St NW','Washington','DC','20005',38.9053,-77.0291,'Northeast','Temperate','A-Tier','Medium'),
    ('STORE','1521 N Milwaukee Ave','Chicago','IL','60622',41.9086,-87.6692,'Midwest','Continental','A-Tier','Medium'),
    ('STORE','1440 3rd St Promenade','Santa Monica','CA','90401',34.0173,-118.4946,'West','Mediterranean','A-Tier','Medium'),
    ('STORE','2621 Guadalupe St','Austin','TX','78705',30.2921,-97.7417,'South','Subtropical','A-Tier','Medium'),
    ('STORE','1130 Broadway','New York','NY','10010',40.7440,-73.9893,'Northeast','Temperate','A-Tier','Large'),
    ('STORE','500 Pine St','Seattle','WA','98101',47.6120,-122.3371,'Northwest','Maritime','A-Tier','Medium'),
    ('STORE','2030 Fillmore St','San Francisco','CA','94115',37.7891,-122.4339,'West','Mediterranean','A-Tier','Medium'),
    ('STORE','342 Newbury St','Boston','MA','02115',42.3487,-71.0856,'Northeast','Temperate','A-Tier','Medium'),
    ('STORE','3307 M St NW','Washington','DC','20007',38.9053,-77.0614,'Northeast','Temperate','B-Tier','Small'),
    ('STORE','1540 N Milwaukee Ave','Chicago','IL','60622',41.9102,-87.6698,'Midwest','Continental','B-Tier','Small'),
    ('STORE','1100 Abbot Kinney Blvd','Venice','CA','90291',33.9889,-118.4684,'West','Mediterranean','B-Tier','Small'),
    ('STORE','1700 Haight St','San Francisco','CA','94117',37.7693,-122.4509,'West','Mediterranean','B-Tier','Small'),
    ('STORE','535 S Lamar Blvd','Austin','TX','78704',30.2554,-97.7601,'South','Subtropical','B-Tier','Medium'),
    ('STORE','1426 Montana Ave','Santa Monica','CA','90403',34.0286,-118.4931,'West','Mediterranean','B-Tier','Small'),
    ('STORE','1020 W Armitage Ave','Chicago','IL','60614',41.9181,-87.6546,'Midwest','Continental','B-Tier','Small'),
    ('STORE','611 S Congress Ave','Austin','TX','78704',30.2501,-97.7502,'South','Subtropical','B-Tier','Small'),
    ('STORE','1809 Walnut St','Philadelphia','PA','19103',39.9504,-75.1720,'Northeast','Temperate','B-Tier','Medium'),
    ('STORE','400 Commons Way','Bridgewater','NJ','08807',40.5963,-74.6042,'Northeast','Temperate','C-Tier','Small'),
    ('INTERNET','Online Fulfillment','Online','NA','00000',0.0,0.0,'National','N/A','Digital','N/A')
  AS t(loc_type, addr, city, st, zip, lat, lon, rgn, clim, tier, sz)
  ) t
);

-- ================================================================
-- 2. ITEM CATALOG — retailer-specific product assortments
-- ================================================================

CREATE OR REPLACE TABLE SPS_RETAIL_AI.SHARED.ITEM (
    ITEM_ID VARCHAR(30) NOT NULL,
    RETAILER_ID VARCHAR(20) NOT NULL,
    SPS_RETAILER_NAME_KEY VARCHAR(255),
    SPS_CUSTOMER_ITEM_KEY VARCHAR(255),
    SPS_ITEM_MAPPING_KEY VARCHAR(255),
    CATEGORY_NAME VARCHAR(100),
    PRODUCT_GROUP_NAME VARCHAR(100),
    GENDER VARCHAR(50),
    STYLE_NUMBER VARCHAR(50),
    STYLE_DESCRIPTION VARCHAR(255),
    COLOR_NAME VARCHAR(100),
    SIZE_NAME VARCHAR(50),
    UPC VARCHAR(50),
    SKU VARCHAR(50),
    URBN_SHORT_SKU VARCHAR(30) COMMENT 'URBN proprietary SKU - only for Urban Outfitters',
    VENDOR_STYLE_NUMBER VARCHAR(100),
    PRODUCT_DESCRIPTION VARCHAR(500),
    MSRP NUMBER(10,2),
    COST NUMBER(10,2),
    BRAND_NAME VARCHAR(100),
    VENDOR_CODE VARCHAR(20),
    VENDOR_NAME VARCHAR(100),
    SUPPLIER_ID VARCHAR(20),
    DEPARTMENT_NAME VARCHAR(100),
    PRODUCT_SEASON VARCHAR(50),
    REPLENISHMENT_INDICATOR VARCHAR(5),
    LAUNCH_DATE DATE,
    EXIT_DATE DATE,
    UNIT_OF_MEASURE VARCHAR(20) DEFAULT 'EA',
    SPS_ITEM_STATUS VARCHAR(20) DEFAULT 'ACTIVE',
    IS_SYNTHETIC BOOLEAN DEFAULT TRUE,
    INSERT_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_ITEM PRIMARY KEY (ITEM_ID)
);

-- Generate Foot Locker items: athletic footwear & apparel with size curves
INSERT INTO SPS_RETAIL_AI.SHARED.ITEM
    (ITEM_ID, RETAILER_ID, SPS_RETAILER_NAME_KEY, SPS_CUSTOMER_ITEM_KEY, SPS_ITEM_MAPPING_KEY,
     CATEGORY_NAME, PRODUCT_GROUP_NAME, GENDER, STYLE_NUMBER, STYLE_DESCRIPTION,
     COLOR_NAME, SIZE_NAME, UPC, VENDOR_STYLE_NUMBER, PRODUCT_DESCRIPTION,
     MSRP, COST, BRAND_NAME, SUPPLIER_ID, DEPARTMENT_NAME, PRODUCT_SEASON,
     REPLENISHMENT_INDICATOR, LAUNCH_DATE)
SELECT
    'FL_ITM_' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 5, '0'),
    'FL', 'Foot Locker',
    'FL_ITM_' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 5, '0'),
    'FL_MAP_' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 5, '0'),
    cat, pg, gen, sty, sty || ' ' || col,
    col, sz,
    '8' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 12, '0'),
    'VS-' || sty || '-' || LEFT(col, 3),
    pg || ' ' || sty || ' ' || col || ' ' || sz,
    base_msrp + (UNIFORM(-10, 15, RANDOM()))::NUMBER(10,2),
    (base_msrp * 0.45 + UNIFORM(-5, 5, RANDOM()))::NUMBER(10,2),
    brand,
    sup_id,
    dept,
    season,
    CASE WHEN UNIFORM(0,10,RANDOM()) > 3 THEN 'Y' ELSE 'N' END,
    DATEADD('day', -UNIFORM(30, 540, RANDOM()), '2024-09-01'::DATE)
FROM (
  SELECT c.cat, c.pg, c.gen, s.sty, s.brand, s.base_msrp, s.dept, s.season, s.sup_id,
         co.col, sz.sz
  FROM (VALUES
    ('FOOTWEAR','SNEAKERS','Mens'),('FOOTWEAR','SNEAKERS','Womens'),('FOOTWEAR','SNEAKERS','Kids'),
    ('FOOTWEAR','BOOTS','Mens'),('FOOTWEAR','BOOTS','Womens'),
    ('FOOTWEAR','SLIDES','Mens'),('FOOTWEAR','SLIDES','Womens'),
    ('APPAREL','TOPS','Mens'),('APPAREL','TOPS','Womens'),
    ('APPAREL','PANTS','Mens'),('APPAREL','PANTS','Womens'),
    ('APPAREL','HEADGEAR','Mens')
  ) AS c(cat, pg, gen)
  CROSS JOIN (VALUES
    ('AX100','Apex Athletics','SUP_001',120.00,'Athletic','Fall 2023'),
    ('AX200','Apex Athletics','SUP_001',95.00,'Athletic','Spring 2024'),
    ('CF300','Coastal Footwear','SUP_005',110.00,'Performance','Fall 2024'),
    ('PS400','Pinnacle Sports','SUP_014',85.00,'Athletic','Year-Round'),
    ('MT500','Metro Style','SUP_007',75.00,'Casual','Spring 2024')
  ) AS s(sty, brand, sup_id, base_msrp, dept, season)
  CROSS JOIN (VALUES ('Black'),('White'),('Red'),('Navy'),('Grey')) AS co(col)
  CROSS JOIN (VALUES ('S'),('M'),('L'),('XL')) AS sz(sz)
  WHERE UNIFORM(0, 10, RANDOM()) > 3
)
LIMIT 500;

-- Generate Bass Pro items: outdoor categories
INSERT INTO SPS_RETAIL_AI.SHARED.ITEM
    (ITEM_ID, RETAILER_ID, SPS_RETAILER_NAME_KEY, SPS_CUSTOMER_ITEM_KEY, SPS_ITEM_MAPPING_KEY,
     CATEGORY_NAME, PRODUCT_GROUP_NAME, GENDER, STYLE_NUMBER, STYLE_DESCRIPTION,
     COLOR_NAME, SIZE_NAME, UPC, VENDOR_STYLE_NUMBER, PRODUCT_DESCRIPTION,
     MSRP, COST, BRAND_NAME, SUPPLIER_ID, DEPARTMENT_NAME, PRODUCT_SEASON,
     REPLENISHMENT_INDICATOR, LAUNCH_DATE)
SELECT
    'BP_ITM_' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 5, '0'),
    'BP', 'Bass Pro Shops',
    'BP_ITM_' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 5, '0'),
    'BP_MAP_' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 5, '0'),
    cat, pg, gen, sty, sty || ' ' || col,
    col, sz,
    '9' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 12, '0'),
    'BP-' || sty || '-' || LEFT(col, 3),
    pg || ' ' || sty || ' ' || col || ' ' || sz,
    base_msrp + (UNIFORM(-10, 20, RANDOM()))::NUMBER(10,2),
    (base_msrp * 0.42 + UNIFORM(-5, 8, RANDOM()))::NUMBER(10,2),
    brand, sup_id, dept, season,
    CASE WHEN UNIFORM(0,10,RANDOM()) > 4 THEN 'Y' ELSE 'N' END,
    DATEADD('day', -UNIFORM(30, 540, RANDOM()), '2024-09-01'::DATE)
FROM (
  SELECT c.cat, c.pg, c.gen, s.sty, s.brand, s.base_msrp, s.dept, s.season, s.sup_id,
         co.col, sz.sz
  FROM (VALUES
    ('OUTDOOR','FISHING GEAR','Mens'),('OUTDOOR','CAMPING GEAR','Mens'),
    ('OUTDOOR','HUNTING APPAREL','Mens'),('OUTDOOR','HUNTING APPAREL','Womens'),
    ('OUTDOOR','BOATING','Mens'),
    ('APPAREL','JACKETS','Mens'),('APPAREL','JACKETS','Womens'),
    ('FOOTWEAR','BOOTS','Mens'),('FOOTWEAR','BOOTS','Womens'),
    ('APPAREL','PANTS','Mens'),('APPAREL','TOPS','Mens'),
    ('OUTDOOR','ACCESSORIES','Mens')
  ) AS c(cat, pg, gen)
  CROSS JOIN (VALUES
    ('SG100','Summit Gear','SUP_002',89.00,'Outdoor','Spring 2024'),
    ('NW200','Northern Outfitters','SUP_006',120.00,'Cold Weather','Fall 2023'),
    ('PW300','Prairie Wind','SUP_017',65.00,'Hunting','Fall 2024'),
    ('HB400','Heritage Boot','SUP_013',145.00,'Workwear','Year-Round'),
    ('BR500','Blue Ridge','SUP_019',55.00,'Camping','Spring 2024')
  ) AS s(sty, brand, sup_id, base_msrp, dept, season)
  CROSS JOIN (VALUES ('Camo'),('Forest Green'),('Brown'),('Tan'),('Black')) AS co(col)
  CROSS JOIN (VALUES ('S'),('M'),('L'),('XL')) AS sz(sz)
  WHERE UNIFORM(0, 10, RANDOM()) > 3
)
LIMIT 500;

-- Generate Urban Outfitters items: fashion/lifestyle with URBN short SKU
INSERT INTO SPS_RETAIL_AI.SHARED.ITEM
    (ITEM_ID, RETAILER_ID, SPS_RETAILER_NAME_KEY, SPS_CUSTOMER_ITEM_KEY, SPS_ITEM_MAPPING_KEY,
     CATEGORY_NAME, PRODUCT_GROUP_NAME, GENDER, STYLE_NUMBER, STYLE_DESCRIPTION,
     COLOR_NAME, SIZE_NAME, UPC, SKU, URBN_SHORT_SKU, VENDOR_STYLE_NUMBER,
     PRODUCT_DESCRIPTION, MSRP, COST, BRAND_NAME, SUPPLIER_ID, DEPARTMENT_NAME,
     PRODUCT_SEASON, REPLENISHMENT_INDICATOR, LAUNCH_DATE)
SELECT
    'UO_ITM_' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 5, '0'),
    'UO', 'Urban Outfitters',
    'UO_ITM_' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 5, '0'),
    'UO_MAP_' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 5, '0'),
    cat, pg, gen, sty, sty || ' ' || col,
    col, sz,
    '7' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 12, '0'),
    NULL,
    'UO' || LPAD(ROW_NUMBER() OVER (ORDER BY cat, pg, gen, sty, col, sz)::VARCHAR, 6, '0'),
    'VND-' || sty || '-' || LEFT(col, 3),
    pg || ' ' || sty || ' ' || col || ' ' || sz,
    base_msrp + (UNIFORM(-8, 15, RANDOM()))::NUMBER(10,2),
    (base_msrp * 0.38 + UNIFORM(-3, 6, RANDOM()))::NUMBER(10,2),
    brand, sup_id, dept, season,
    CASE WHEN UNIFORM(0,10,RANDOM()) > 5 THEN 'Y' ELSE 'N' END,
    DATEADD('day', -UNIFORM(30, 540, RANDOM()), '2024-09-01'::DATE)
FROM (
  SELECT c.cat, c.pg, c.gen, s.sty, s.brand, s.base_msrp, s.dept, s.season, s.sup_id,
         co.col, sz.sz
  FROM (VALUES
    ('APPAREL','DRESSES','Womens'),('APPAREL','TOPS','Womens'),('APPAREL','TOPS','Mens'),
    ('APPAREL','PANTS','Womens'),('APPAREL','PANTS','Mens'),
    ('APPAREL','JACKETS','Womens'),('APPAREL','JACKETS','Mens'),
    ('APPAREL','SKIRTS','Womens'),
    ('ACCESSORIES','BAGS','Womens'),('ACCESSORIES','JEWELRY','Womens'),
    ('HOME','DECOR','Unisex'),('HOME','BEDDING','Unisex')
  ) AS c(cat, pg, gen)
  CROSS JOIN (VALUES
    ('MS100','Metro Style','SUP_007',68.00,'Fashion','Fall 2024'),
    ('ET200','Eastbound Textiles','SUP_004',52.00,'Fashion','Spring 2024'),
    ('PT300','Pacific Trail','SUP_003',45.00,'Casual','Year-Round'),
    ('TW400','Tidewater Apparel','SUP_011',58.00,'Casual','Summer 2024'),
    ('HT500','Harbor Trading','SUP_018',35.00,'Accessories','Year-Round')
  ) AS s(sty, brand, sup_id, base_msrp, dept, season)
  CROSS JOIN (VALUES ('Sage'),('Terracotta'),('Ivory'),('Charcoal'),('Dusty Rose')) AS co(col)
  CROSS JOIN (VALUES ('XS'),('S'),('M'),('L')) AS sz(sz)
  WHERE UNIFORM(0, 10, RANDOM()) > 3
)
LIMIT 500;

-- ================================================================
-- 3. RETAIL CALENDAR — 2-year weekly spine (Sep 2022 - Sep 2024)
-- ================================================================

CREATE OR REPLACE TABLE SPS_RETAIL_AI.SHARED.RETAIL_CALENDAR (
    CALENDAR_DATE DATE NOT NULL,
    FISCAL_WEEK VARCHAR(10),
    FISCAL_YEAR NUMBER(4,0),
    WEEK_NUMBER NUMBER(2,0),
    MONTH_NAME VARCHAR(20),
    QUARTER VARCHAR(5),
    SEASON VARCHAR(20),
    IS_HOLIDAY_WEEK BOOLEAN DEFAULT FALSE,
    HOLIDAY_NAME VARCHAR(50),
    CONSTRAINT PK_CALENDAR PRIMARY KEY (CALENDAR_DATE)
);

INSERT INTO SPS_RETAIL_AI.SHARED.RETAIL_CALENDAR
SELECT
    dt,
    YEAR(dt)::VARCHAR || '-W' || LPAD(WEEKOFYEAR(dt)::VARCHAR, 2, '0'),
    YEAR(dt),
    WEEKOFYEAR(dt),
    MONTHNAME(dt),
    'Q' || QUARTER(dt),
    CASE
        WHEN MONTH(dt) IN (3,4,5) THEN 'Spring'
        WHEN MONTH(dt) IN (6,7,8) THEN 'Summer'
        WHEN MONTH(dt) IN (9,10,11) THEN 'Fall'
        ELSE 'Winter'
    END,
    CASE WHEN WEEKOFYEAR(dt) IN (47,48,51,52,1) OR (MONTH(dt)=7 AND DAY(dt) BETWEEN 1 AND 7) THEN TRUE ELSE FALSE END,
    CASE
        WHEN WEEKOFYEAR(dt) IN (47,48) THEN 'Black Friday / Cyber Monday'
        WHEN WEEKOFYEAR(dt) IN (51,52) THEN 'Christmas'
        WHEN WEEKOFYEAR(dt) = 1 THEN 'New Year'
        WHEN MONTH(dt) = 7 AND DAY(dt) BETWEEN 1 AND 7 THEN 'July 4th'
        ELSE NULL
    END
FROM (
    SELECT DATEADD('week', seq4(), '2022-09-03'::DATE) AS dt
    FROM TABLE(GENERATOR(ROWCOUNT => 105))
)
WHERE dt <= '2024-09-07'::DATE;

RETURN 'Phase 1 complete: ' || 
    (SELECT COUNT(*) FROM SPS_RETAIL_AI.SHARED.LOCATION)::VARCHAR || ' locations, ' ||
    (SELECT COUNT(*) FROM SPS_RETAIL_AI.SHARED.ITEM)::VARCHAR || ' items, ' ||
    (SELECT COUNT(*) FROM SPS_RETAIL_AI.SHARED.RETAIL_CALENDAR)::VARCHAR || ' calendar weeks, ' ||
    (SELECT COUNT(*) FROM SPS_RETAIL_AI.SHARED.SUPPLIER)::VARCHAR || ' suppliers';

END;
