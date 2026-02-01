export async function updateLocationDetails(q, elements) {
    const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}`
    );
    const data = await res.json();

    if (!data[0]) return;

    const { lat, lon } = data[0];
    elements.lat.value = lat;
    elements.lng.value = lon;

    const elevRes = await fetch(`/get_elevation?lat=${lat}&lon=${lon}`);
    const elevData = await elevRes.text();
    if (elevData) {
        elements.elev.value = elevData;
    }
}
