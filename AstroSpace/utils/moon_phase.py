import ephem


def get_moon_illumination(date_str):
    date_str = date_str.strftime("%Y-%m-%d 01:00:00")
    observer = ephem.Observer()
    observer.date = date_str

    moon = ephem.Moon(observer)

    illumination = moon.phase  # In percent

    # Get moon age in days
    prev_new = ephem.previous_new_moon(observer.date)
    next_new = ephem.next_new_moon(observer.date)
    lunation_length = next_new - prev_new
    moon_age = observer.date - prev_new
    phase_frac = moon_age / lunation_length

    # Determine phase
    if phase_frac < 0.02:
        phase = "New Moon"
    elif phase_frac < 0.25:
        phase = "Waxing Crescent"
    elif phase_frac < 0.27:
        phase = "First Quarter"
    elif phase_frac < 0.50:
        phase = "Waxing Gibbous"
    elif phase_frac < 0.52:
        phase = "Full Moon"
    elif phase_frac < 0.75:
        phase = "Waning Gibbous"
    elif phase_frac < 0.77:
        phase = "Last Quarter"
    else:
        phase = "Waning Crescent"

    return round(illumination, 2), phase
