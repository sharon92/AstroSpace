-- Equipment inventory
CREATE TABLE camera (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    sensor_type TEXT,
    sensor_name TEXT,
    sensor_width FLOAT,
    sensor_height FLOAT,
    sensor_diagonal FLOAT,
    pixel_size FLOAT,
    pixel_count_x INT,
    pixel_count_y INT,
    unity_gain INT,
    bit_depth INT CHECK (bit_depth IN (8, 10, 12, 14, 16)),
    well_capacity FLOAT,
    read_noise FLOAT,
    quantum_efficiency FLOAT,
    color_camera BOOLEAN DEFAULT true,
    brand TEXT,
    link TEXT
);

CREATE TABLE telescope (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('refractor', 'reflector', 'catadioptric', 'ritchey-chretien')),
    aperture FLOAT,
    focal_length FLOAT,
    f_ratio FLOAT,
    brand TEXT,
    link TEXT
);

CREATE TABLE reducer(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,
    backfocus INT,
    reduction_ratio FLOAT,
    brand TEXT,
    link TEXT
);

CREATE TABLE mount(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('equatorial', 'altazimuth')),
    payload_capacity FLOAT,
    brand TEXT,
    link TEXT
);

CREATE TABLE tripod(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    payload_capacity FLOAT,
    brand TEXT,
    link TEXT
);

CREATE TABLE cam_filter(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,
    bandpass FLOAT,
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
    type TEXT CHECK (type IN ('manual', 'motorized')),
    filter_count INT,
    brand TEXT,
    link TEXT
);

CREATE TABLE rotator (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('manual', 'motorized')),
    brand TEXT,
    link TEXT
);

CREATE TABLE software (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('acquisition', 'processing')) NOT NULL,
    link TEXT,
    metadata TEXT
);

CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    short_description TEXT,
    description TEXT,
    author TEXT,
    image_path TEXT,
    image_thumbnail TEXT,
    pixel_scale FLOAT DEFAULT 1.0 NOT NULL,
    object_type TEXT,
    header_json TEXT,
    overlays_json TEXT,
    meta_json TEXT,
    location TEXT,
    location_latitude FLOAT,
    location_longitude FLOAT,
    location_elevation FLOAT,
    guide_log TEXT,
    guiding_plot_json JSONB,
    calibration_plot_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    rotator_id INT REFERENCES rotator(id)
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
    UNIQUE(image_id, user_id)
);

CREATE TABLE image_comments (
    id SERIAL PRIMARY KEY,
    image_id INTEGER REFERENCES images(id),
    ip_address TEXT,
    comment TEXT NOT NULL,
    commented_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    commented_by TEXT
);

CREATE TABLE capture_dates (
    id SERIAL PRIMARY KEY,
    image_id INT REFERENCES images(id) ON DELETE CASCADE,
    capture_date DATE NOT NULL,
    moon_illumination FLOAT,
    moon_phase TEXT,
    mean_temperature FLOAT,
    mean_humidity FLOAT,
    mean_wind_speed FLOAT,
    mean_seeing_quality TEXT
);

CREATE TABLE image_lights (
    id SERIAL PRIMARY KEY,
    image_id INT REFERENCES images(id) ON DELETE CASCADE,
    cam_filter TEXT NOT NULL,
    light_count INT NOT NULL,
    exposure_time INT,
    gain INT,
    offset_cam INT,
    temperature FLOAT
);

CREATE TABLE image_software (
    id SERIAL PRIMARY KEY,
    image_id INT REFERENCES images(id) ON DELETE CASCADE,
    software_id INT REFERENCES software(id) ON DELETE CASCADE
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
  telescopius_api_key TEXT
);

CREATE TABLE web_info (
    id SERIAL PRIMARY KEY,
    site_name TEXT,
    site_description TEXT,
    welcome_message TEXT,
    contact_email TEXT,
    social_links JSONB
);

INSERT INTO camera (name, sensor_type, sensor_name, sensor_width, sensor_height, sensor_diagonal, pixel_size, pixel_count_x, pixel_count_y, unity_gain, bit_depth, well_capacity, read_noise, quantum_efficiency, color_camera, brand, link)
VALUES
('VeTec571c', 'APS-C', 'Sony IMX571', 23.5, 15.7, 28.3, 3.8, 6224, 4168, 100, 16, 50000, 1.5, 80, true, 'Omegon', 'https://www.astroshop.de/p,67320'),
('ASI174MM Mini', '1/1.2"', 'Sony IMX249', 11.34, 7.13, 13.4, 5.86, 1936, 1216, 180, 12, 32400, 3.5, 77, false, 'ZWO', 'https://www.zwoastro.com/product/mini-cameras/'),
('ASI120MM Mini', '1/3"', 'AR0130CS', 4.8, 3.6, 6.1, 3.75, 1280, 960, 29, 12, 14500, 4.0, 80, false, 'ZWO', 'https://www.zwoastro.com/product/mini-cameras/');

INSERT INTO telescope (name, type, aperture, focal_length, f_ratio, brand, link)
VALUES
('Evolux-82ED', 'refractor', 82.0, 530.0, 6.45, 'Skywatcher', 'https://www.astroshop.de/p,75232'),
('Ritchey-Chretien Pro RC203/1624', 'ritchey-chretien', 203.0, 1624.0, 8.0, 'Omegon', 'https://www.omegon.eu/telescopes/omegon-ritchey-chretien-pro-rc-203-1624-ota/p,53810'),
('SV165', 'refractor', 40, 160.0, 4.0, 'Svbony', 'https://www.amazon.de/-/en/dp/B0BR5JBRPK?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_3&th=1');

INSERT INTO reducer (name, type, backfocus, reduction_ratio, brand, link)
VALUES
('Flatenner 0.9x Evolux-82ED', 'flattener-reducer', 55, 0.9, 'Skywatcher', 'https://www.astroshop.de/flattener-korrektoren-reducer/skywatcher-flattener-0-9x-evolux-82ed/p,75234'),
('TS-Optics 2" Reducer 0,67x', 'reducer', 85, 0.67, 'TS-Optics', 'https://www.teleskop-express.de/de/astrofotografie-und-fotografie-15/bildfeld-korrektoren-fuer-teleskope-138/ts-optics-2-ccd-reducer-0-67x-fuer-rc-flatfield-teleskope-bis-f-8-8932');

INSERT INTO mount (name, type, payload_capacity, brand, link)
VALUES
('AM5N', 'equatorial', 15.0, 'ZWO', 'https://www.teleskop-spezialisten.de/shop/Montierungen/Parallaktisch-GoTo-Nachfuehrung/ZWO-AM5N-Harmonic-Equatorial-Mount-Gen-2-GoTo-Reisemontierung-Montierungskopf-AM5-N::7025.html'),
('HEQ5-Pro', 'equatorial', 14.0, 'Skywatcher', 'https://www.astroshop.eu/equatorial-with-goto/skywatcher-mount-heq-5-pro-synscan-goto/p,4071');

INSERT INTO tripod (name, payload_capacity, brand, link)
VALUES
('Carbon Fiber Tripod TC40', 50.0, 'ZWO', 'https://www.astroshop.de/stative/zwo-stativ-tc40-fuer-am5-am3/p,75629?utm_medium=cpc&utm_term=75629&utm_campaign=2505&utm_source=froogle&gclid=EAIaIQobChMIreXsnb6PjQMV0JGDBx0ZtgFIEAQYASABEgJy4vD_BwE&utm_content='),
('Steel Tripod', 45.0, 'Skywatcher', 'https://www.teleskop-haus.de/p/sky-watcher-stativ-edelstahl-fuer-eq5-heq5-skytee');

INSERT INTO cam_filter (name, type, bandpass, brand, link)
VALUES
('NO FILTER', '', 0.0, '', ''),
('UHC LightPollution Filter', 'Broadband', 0.0, 'Svbony', 'https://www.amazon.de/-/en/dp/B07G943LQ3?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_4&th=1'),
('SV220 Dual Narrowband Filter', 'Dual Narrowband HaOIII', 7.0, 'Svbony', 'https://www.amazon.de/SV220-Narrowband-Pollution-Telescopic-Astrophotography/dp/B0BRNCM74M/ref=sr_1_1_sspa?crid=LFQE2NU0C09T&dib=eyJ2IjoiMSJ9.F_-98BjPIqQGBZ4aKOqAmf9Q2aGarvpWquWBj8y88liBMkLDkt9f_A4aU5BOQwbv5Y9vWNGu2OLFyvS_8ehPkRTU3A56Ofo5Hcoi1UF9-S8.WPPfCRAEEZ0QgFN3FnOFY4OtyAuKoR17Mpr44xfBWW0&dib_tag=se&keywords=Svbony%2Bdual%2Bnarrowband&qid=1746558833&s=ce-de&sprefix=svbony%2Bdual%2Bnarrowband%2Celectronics%2C112&sr=1-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&th=1');

INSERT INTO filter_wheel (name, type, filter_count, brand, link)
VALUES
('SV226', 'manual', 1, 'Svbony', 'https://www.kaufland.de/product/491672850/?kwd=&source=pla&sid=36016207&utm_source=google&utm_medium=cpc&utm_id=22027054293&gad_source=1&gad_campaignid=22027094106&gbraid=0AAAAADprSmGxVOVvlfvG5qG9sj8b8imWc&gclid=EAIaIQobChMImuiMrL-PjQMVpZGDBx38kzRpEAQYASABEgIzuPD_BwE');

INSERT INTO eaf (name, brand, link)
VALUES
('Gemini Automatic Star Focuser Pro', 'Gemini', 'https://de.aliexpress.com/item/1005006731851010.html?src=google&pdp_npi=4%40dis!EUR!64.39!64.39!!!!!%40!12000038121917954!ppc!!!&src=google&albch=shopping&acnt=272-267-0231&isdl=y&slnk=&plac=&mtctp=&albbt=Google_7_shopping&aff_platform=google&aff_short_key=UneMJZVf&gclsrc=aw.ds&&albagn=888888&&ds_e_adid=&ds_e_matchtype=&ds_e_device=c&ds_e_network=x&ds_e_product_group_id=&ds_e_product_id=de1005006731851010&ds_e_product_merchant_id=109388906&ds_e_product_country=DE&ds_e_product_language=de&ds_e_product_channel=online&ds_e_product_store_id=&ds_url_v=2&albcp=20536664094&albag=&isSmbAutoCall=false&needSmbHouyi=false&gad_source=1&gad_campaignid=19235627950&gbraid=0AAAAAoukdWNIXl5dTjvVN_BN8OMDHdHWj&gclid=EAIaIQobChMIssOXxb-PjQMVq5JQBh14GSp9EAQYASABEgIidvD_BwE');

INSERT INTO dew_heater (name, brand, link)
VALUES
('SV172', 'Svbony', 'https://www.amazon.de/Svbony-SV172-Tauheizstreifen-Temperaturregler-Feuchtigkeit/dp/B08F2D5V7S/ref=asc_df_B08F2D5V7S?mcid=8a3589cfa09d3bd1bcc842e056d26422&th=1&tag=googshopde-21&linkCode=df0&hvadid=696222049809&hvpos=&hvnetw=g&hvrand=16013134872152345626&hvpone=&hvptwo=&hvqmt=&hvdev=c&hvdvcmdl=&hvlocint=&hvlocphy=9068167&hvtargid=pla-1093538094946&hvocijid=16013134872152345626-B08F2D5V7S-&hvexpln=0');

INSERT INTO flat_panel (name, brand, link)
VALUES
('A3 Light Pad', 'WELZK', 'https://amzn.eu/d/dPR02xD');

INSERT INTO rotator (name, type, brand, link)
VALUES
('ZWO Rotator CAA', 'motorized', 'ZWO', 'https://www.astroshop.eu/rotators/zwo-rotator-caa/p,85387');

INSERT INTO guider (name, link)
VALUES
('Askar Off-Axis-Guider', 'https://www.astroshop.de/off-axis-guider/askar-off-axis-guider-t2-m48-m54/p,77132'),
('Svbony SV165', 'https://www.amazon.de/-/en/dp/B0BR5JBRPK?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_3&th=1');

INSERT INTO software (name, type, link, metadata)
VALUES
('N.I.N.A', 'acquisition', 'https://nighttime-imaging.eu', ''),
('PHD2 Guiding', 'acquisition', 'https://openphdguiding.org', ''),
('Stellarium', 'acquisition', 'https://stellarium.org', ''),
('Touch-N-Stars', 'acquisition', 'https://github.com/Touch-N-Stars/Touch-N-Stars', ''),
('PixInsight', 'processing', 'https://pixinsight.com', '<a href="https://pixinsight.com/"><img src="/static/assets/images/pixinsight-140x40-black.en.png" width="140" height="40" /></a>'),
('RCAstro', 'processing', 'https://rcastro.com', ''),
('GIMP', 'processing', 'https://www.gimp.org', '');
