DROP TABLE IF EXISTS 
    camera,
    capture_dates,
    dew_heater,
    eaf,
    cam_filter,
    filter_wheel,
    rotator,
    flat_panel,
    image_lights,
    image_software,
    images,
    image_views,
    image_likes,
    image_comments,
    mount,
    guider,
    reducer,
    software,
    telescope,
    tripod,
    users,
    blogs,
    blog_views,
    blog_likes,
    blog_comments
CASCADE;


-- Equipment inventory
CREATE TABLE camera (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    sensor_type TEXT, --APS-C, APS-H, full-frame, etc.
    sensor_name TEXT, -- Sony IMX571
    sensor_width FLOAT, -- in mm
    sensor_height FLOAT, -- in mm
    sensor_diagonal FLOAT, -- in mm
    pixel_size FLOAT, -- in microns
    pixel_count_x INT, -- horizontal pixel count
    pixel_count_y INT, -- vertical pixel count
    unity_gain INT, -- unity gain in e-/ADU
    bit_depth INT CHECK (bit_depth IN (8, 10, 12, 14, 16)), -- e.g., 8, 10, 12, 14, or 16 bits
    well_capacity FLOAT, -- in e- (electrons)
    read_noise FLOAT, -- in e- (electrons)
    quantum_efficiency FLOAT, -- in percentage (0-100)
    color_camera BOOLEAN DEFAULT true, -- true if color camera, false if monochrome
    brand TEXT,
    link TEXT
);

CREATE TABLE telescope (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('refractor', 'reflector', 'catadioptric', 'ritchey-chretien')), -- e.g., refractor, reflector, catadioptric
    aperture FLOAT, -- in mm
    focal_length FLOAT, -- in mm
    f_ratio FLOAT, -- f/ratio
    brand TEXT,
    link TEXT
);

CREATE TABLE reducer(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT, -- e.g., focal reducer, flattener
    backfocus INT, -- in mm
    reduction_ratio FLOAT, -- e.g., 0.8x
    brand TEXT,
    link TEXT
);

CREATE TABLE mount(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('equatorial', 'altazimuth')), -- e.g., equatorial, altazimuth
    payload_capacity FLOAT, -- in kg
    brand TEXT,
    link TEXT
);

CREATE TABLE tripod(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    payload_capacity FLOAT, -- in kg
    brand TEXT,
    link TEXT
);

CREATE TABLE cam_filter(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT , -- e.g., L, R, G, B, Ha, OIII, SII
    bandpass FLOAT, -- in nm
    brand TEXT,
    link TEXT
);

CREATE TABLE eaf(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    brand TEXT,
    link TEXT
);

CREATE TABLE dew_heater(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    brand TEXT,
    link TEXT
);

CREATE TABLE flat_panel(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    brand TEXT,
    link TEXT
);

CREATE TABLE guider(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    link TEXT
);

CREATE TABLE filter_wheel (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('manual', 'motorized')), -- e.g., manual, motorized
    filter_count INT, -- number of filters
    brand TEXT,
    link TEXT
);

CREATE TABLE rotator (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('manual', 'motorized')), -- e.g., manual, motorized
    brand TEXT,
    link TEXT
);

-- Acquisition/processing software table
CREATE TABLE software (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('acquisition', 'processing')) NOT NULL,
    link TEXT,
    metadata TEXT
);

-- Main image/posts table
CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    short_description TEXT, -- short description for previews
    description TEXT,
    author TEXT, -- username or email of the uploader
    image_path TEXT,
    image_thumbnail TEXT,
    pixel_scale FLOAT DEFAULT 1.0 NOT NULL, -- in arcseconds per pixel
    object_type TEXT, -- e.g., galaxy, nebula, star cluster
    header_json TEXT, -- JSON string with FITS header information
    overlays_json TEXT, -- JSON string with overlay information (e.g., annotations, labels)

    location TEXT, -- e.g., observatory name or location
    location_latitude FLOAT, -- in degrees
    location_longitude FLOAT, -- in degrees
    location_elevation FLOAT, -- in meters above sea level

    guide_log TEXT, -- path to the guiding log file
    guiding_html TEXT, -- bokeh HTML file for interactive visualization
    calibration_html TEXT, -- bokeh HTML file for calibration visualization
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys to equipment tables
    camera_id INT REFERENCES camera(id),
    telescope_id INT REFERENCES telescope(id),
    reducer_id INT REFERENCES reducer(id),
    mount_id INT REFERENCES mount(id),
    tripod_id INT REFERENCES tripod(id),
    filter_wheel_id INT REFERENCES filter_wheel(id),
    eaf_id INT REFERENCES eaf(id),
    dew_heater_id INT REFERENCES dew_heater(id),
    flat_panel_id INT REFERENCES flat_panel(id),
    guide_camera_id INT REFERENCES camera(id),
    guider_id INT REFERENCES guider(id),
    rotator_id INT REFERENCES rotator(id) -- assuming rotator uses the same EAF table
);

CREATE TABLE image_views (
    id SERIAL PRIMARY KEY,
    image_id INTEGER REFERENCES images(id),
    user_id TEXT,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE image_likes (
    id SERIAL PRIMARY KEY,
    image_id INTEGER REFERENCES images(id),
    user_id TEXT,
    liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(image_id, user_id)  -- prevents multiple likes from same IP
);

CREATE TABLE image_comments (
    id SERIAL PRIMARY KEY,
    image_id INTEGER REFERENCES images(id),
    ip_address TEXT,
    comment TEXT NOT NULL,
    commented_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    commented_by TEXT -- username or email of the commenter
);

CREATE TABLE capture_dates (
    id SERIAL PRIMARY KEY,
    image_id INT REFERENCES images(id) ON DELETE CASCADE,
    capture_date DATE NOT NULL,
    moon_illumination FLOAT, -- in percentage (0-100)
    moon_phase TEXT, -- e.g., new moon, first quarter, full moon, last quarter
    mean_temperature FLOAT, -- in Celsius
    mean_humidity FLOAT, -- in percentage (0-100)
    mean_wind_speed FLOAT, -- in km/h
    mean_seeing_quality TEXT -- e.g., excellent, good, fair, poor
);

-- Lights per filter for each image
CREATE TABLE image_lights (
    id SERIAL PRIMARY KEY,
    image_id INT REFERENCES images(id) ON DELETE CASCADE,
    cam_filter TEXT NOT NULL,           -- e.g., L, R, G, B, Ha
    light_count INT NOT NULL,       -- number of subs
    exposure_time INT,            -- in seconds
    gain INT,                     -- in e-/ADU
    offset_cam INT,                   -- in ADU
    temperature FLOAT               -- in Celsius
);


-- Link table for software used per image (many-to-many)
CREATE TABLE image_software (
    id SERIAL PRIMARY KEY,
    image_id INT REFERENCES images(id) ON DELETE CASCADE,
    software_id INT REFERENCES software(id) ON DELETE CASCADE
);

CREATE TABLE blogs (
  id SERIAL PRIMARY KEY,
  blog_html TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  metadata TEXT
);

CREATE TABLE blog_views (
    id SERIAL PRIMARY KEY,
    blog_id INTEGER REFERENCES blogs(id),
    user_id TEXT,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blog_likes (
    id SERIAL PRIMARY KEY,
    blog_id INTEGER REFERENCES blogs(id),
    user_id TEXT,
    liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(blog_id, user_id)  -- prevents multiple likes from same IP
);

CREATE TABLE blog_comments (
    id SERIAL PRIMARY KEY,
    blog_id INTEGER REFERENCES blogs(id),
    ip_address TEXT,
    comment TEXT NOT NULL,
    commented_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    commented_by TEXT -- username or email of the commenter
);

CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  admin BOOLEAN DEFAULT false,
  display_name TEXT,
  display_image TEXT,
  bio TEXT,
  astrometry_api_key TEXT,
  open_weather_api_key TEXT,
  telescopius_api_key TEXT,
);

CREATE TABLE web_info (
    id SERIAL PRIMARY KEY,
    site_name TEXT,
    site_description TEXT,
    welcome_message TEXT,
    contact_email TEXT,
    social_links JSONB -- e.g., {"twitter": "url", "facebook": "url"}
);

-- Camera
INSERT INTO camera (name, sensor_type, sensor_name, sensor_width, sensor_height, sensor_diagonal, pixel_size, pixel_count_x, pixel_count_y, unity_gain, bit_depth, well_capacity, read_noise, quantum_efficiency, color_camera, brand, link)
VALUES
('VeTec571c', 'APS-C', 'Sony IMX571', 23.5, 15.7, 28.3, 3.8, 6224, 4168, 100, 16, 50000, 1.5, 80, true, 'Omegon', 'https://www.astroshop.de/p,67320'),
('ASI174MM Mini', '1/1.2"', 'Sony IMX249', 11.34, 7.13, 13.4, 5.86, 1936, 1216, 180, 12, 32400, 3.5, 77, false, 'ZWO', 'https://www.zwoastro.com/product/mini-cameras/'),
('ASI120MM Mini', '1/3"', 'AR0130CS', 4.8, 3.6, 6.1, 3.75, 1280, 960, 29, 12, 14500, 4.0, 80, false, 'ZWO', 'https://www.zwoastro.com/product/mini-cameras/');

-- Telescope
INSERT INTO telescope (name, type, aperture, focal_length, f_ratio, brand, link)
VALUES 
('Evolux-82ED', 'refractor', 82.0, 530.0, 6.45, 'Skywatcher', 'https://www.astroshop.de/p,75232'),
('Ritchey-Chretien Pro RC203/1624', 'ritchey-chretien', 203.0, 1624.0, 8.0, 'Omegon', 'https://www.omegon.eu/telescopes/omegon-ritchey-chretien-pro-rc-203-1624-ota/p,53810'),
('SV165', 'refractor', 40, 160.0, 4.0, 'Svbony', 'https://www.amazon.de/-/en/dp/B0BR5JBRPK?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_3&th=1');

-- Reducer
INSERT INTO reducer (name, type, backfocus, reduction_ratio, brand, link)
VALUES 
('Flatenner 0.9x Evolux-82ED', 'flattener-reducer', 55, 0.9, 'Skywatcher', 'https://www.astroshop.de/flattener-korrektoren-reducer/skywatcher-flattener-0-9x-evolux-82ed/p,75234'),
('TS-Optics 2" Reducer 0,67x', 'reducer', 85, 0.67, 'TS-Optics', 'https://www.teleskop-express.de/de/astrofotografie-und-fotografie-15/bildfeld-korrektoren-fuer-teleskope-138/ts-optics-2-ccd-reducer-0-67x-fuer-rc-flatfield-teleskope-bis-f-8-8932');

-- Mount
INSERT INTO mount (name, type, payload_capacity, brand, link)
VALUES 
('AM5N', 'equatorial', 15.0, 'ZWO', 'https://www.teleskop-spezialisten.de/shop/Montierungen/Parallaktisch-GoTo-Nachfuehrung/ZWO-AM5N-Harmonic-Equatorial-Mount-Gen-2-GoTo-Reisemontierung-Montierungskopf-AM5-N::7025.html'),
('HEQ5-Pro', 'equatorial', 14.0, 'Skywatcher', 'https://www.astroshop.eu/equatorial-with-goto/skywatcher-mount-heq-5-pro-synscan-goto/p,4071');

-- Tripod
INSERT INTO tripod (name, payload_capacity,  brand, link)
VALUES ('Carbon Fiber Tripod TC40', 50.0, 'ZWO', 'https://www.astroshop.de/stative/zwo-stativ-tc40-fuer-am5-am3/p,75629?utm_medium=cpc&utm_term=75629&utm_campaign=2505&utm_source=froogle&gclid=EAIaIQobChMIreXsnb6PjQMV0JGDBx0ZtgFIEAQYASABEgJy4vD_BwE&utm_content='),
('Steel Tripod', 45.0, 'Skywatcher', 'https://www.teleskop-haus.de/p/sky-watcher-stativ-edelstahl-fuer-eq5-heq5-skytee');

--Filters
INSERT INTO cam_filter (name, type, bandpass, brand, link)
VALUES 
('NO FILTER','',0.0,'', ''),
('UHC LightPollution Filter', 'Broadband', 0.0, 'Svbony', 'https://www.amazon.de/-/en/dp/B07G943LQ3?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_4&th=1'),
('SV220 Dual Narrowband Filter', 'Dual Narrowband HaOIII', 7.0, 'Svbony', 'https://www.amazon.de/SV220-Narrowband-Pollution-Telescopic-Astrophotography/dp/B0BRNCM74M/ref=sr_1_1_sspa?crid=LFQE2NU0C09T&dib=eyJ2IjoiMSJ9.F_-98BjPIqQGBZ4aKOqAmf9Q2aGarvpWquWBj8y88liBMkLDkt9f_A4aU5BOQwbv5Y9vWNGu2OLFyvS_8ehPkRTU3A56Ofo5Hcoi1UF9-S8.WPPfCRAEEZ0QgFN3FnOFY4OtyAuKoR17Mpr44xfBWW0&dib_tag=se&keywords=Svbony%2Bdual%2Bnarrowband&qid=1746558833&s=ce-de&sprefix=svbony%2Bdual%2Bnarrowband%2Celectronics%2C112&sr=1-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&th=1');

-- Filter Wheel
INSERT INTO filter_wheel (name, type, filter_count, brand, link)
VALUES ('SV226', 'manual', 1, 'Svbony', 'https://www.kaufland.de/product/491672850/?kwd=&source=pla&sid=36016207&utm_source=google&utm_medium=cpc&utm_id=22027054293&gad_source=1&gad_campaignid=22027094106&gbraid=0AAAAADprSmGxVOVvlfvG5qG9sj8b8imWc&gclid=EAIaIQobChMImuiMrL-PjQMVpZGDBx38kzRpEAQYASABEgIzuPD_BwE');

-- EAF
INSERT INTO eaf (name, brand, link)
VALUES ('Gemini Automatic Star Focuser Pro', 'Gemini', 'https://de.aliexpress.com/item/1005006731851010.html?src=google&pdp_npi=4%40dis!EUR!64.39!64.39!!!!!%40!12000038121917954!ppc!!!&src=google&albch=shopping&acnt=272-267-0231&isdl=y&slnk=&plac=&mtctp=&albbt=Google_7_shopping&aff_platform=google&aff_short_key=UneMJZVf&gclsrc=aw.ds&&albagn=888888&&ds_e_adid=&ds_e_matchtype=&ds_e_device=c&ds_e_network=x&ds_e_product_group_id=&ds_e_product_id=de1005006731851010&ds_e_product_merchant_id=109388906&ds_e_product_country=DE&ds_e_product_language=de&ds_e_product_channel=online&ds_e_product_store_id=&ds_url_v=2&albcp=20536664094&albag=&isSmbAutoCall=false&needSmbHouyi=false&gad_source=1&gad_campaignid=19235627950&gbraid=0AAAAAoukdWNIXl5dTjvVN_BN8OMDHdHWj&gclid=EAIaIQobChMIssOXxb-PjQMVq5JQBh14GSp9EAQYASABEgIidvD_BwE');

-- Dew Heater
INSERT INTO dew_heater (name, brand, link)
VALUES ('SV172', 'Svbony', 'https://www.amazon.de/Svbony-SV172-Tauheizstreifen-Temperaturregler-Feuchtigkeit/dp/B08F2D5V7S/ref=asc_df_B08F2D5V7S?mcid=8a3589cfa09d3bd1bcc842e056d26422&th=1&tag=googshopde-21&linkCode=df0&hvadid=696222049809&hvpos=&hvnetw=g&hvrand=16013134872152345626&hvpone=&hvptwo=&hvqmt=&hvdev=c&hvdvcmdl=&hvlocint=&hvlocphy=9068167&hvtargid=pla-1093538094946&hvocijid=16013134872152345626-B08F2D5V7S-&hvexpln=0');

-- Flat Panel
INSERT INTO flat_panel (name, brand, link)
VALUES 
('A3 Light Pad', 'WELZK', 'https://amzn.eu/d/dPR02xD');

-- Rotator
INSERT INTO rotator (name, type, brand, link)
VALUES 
('ZWO Rotator CAA', 'motorized', 'ZWO', 'https://www.astroshop.eu/rotators/zwo-rotator-caa/p,85387');

-- Off Axis Guider
INSERT INTO guider (name, link)
VALUES 
('Askar Off-Axis-Guider', 'https://www.astroshop.de/off-axis-guider/askar-off-axis-guider-t2-m48-m54/p,77132'),
('Svbony SV165',  'https://www.amazon.de/-/en/dp/B0BR5JBRPK?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_3&th=1');

-- Software entries
INSERT INTO software (name, type, link, metadata)
VALUES
('N.I.N.A', 'acquisition', 'https://nighttime-imaging.eu',''),
('PHD2 Guiding', 'acquisition', 'https://openphdguiding.org', ''),
('Stellarium', 'acquisition', 'https://stellarium.org',''),
('Touch-N-Stars', 'acquisition', 'https://github.com/Touch-N-Stars/Touch-N-Stars', ''),
('PixInsight', 'processing', 'https://pixinsight.com', '<a href="https://pixinsight.com/"><img src="/static/assets/images/pixinsight-140x40-black.en.png" width="140" height="40" /></a>'),
('RCAstro', 'processing', 'https://rcastro.com',''),
('GIMP', 'processing', 'https://www.gimp.org','');
