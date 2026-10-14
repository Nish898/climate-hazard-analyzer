import { MapContainer, TileLayer, Marker, Rectangle, useMapEvents, useMap } from "react-leaflet";
import L from "leaflet";
import { useEffect } from "react";

// Leaflet's default marker icons break under bundlers; use CDN assets.
const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

function Clicks({ onPick }) {
  useMapEvents({ click: (e) => onPick(+e.latlng.lat.toFixed(3), +e.latlng.lng.toFixed(3)) });
  return null;
}

function Fly({ lat, lon }) {
  const map = useMap();
  useEffect(() => {
    if (Number.isFinite(lat) && Number.isFinite(lon)) map.flyTo([lat, lon], Math.max(map.getZoom(), 5));
  }, [lat, lon]); // eslint-disable-line
  return null;
}

export default function MapPicker({ form, onPick }) {
  const lat = parseFloat(form.lat), lon = parseFloat(form.lon);
  const lat2 = parseFloat(form.lat2), lon2 = parseFloat(form.lon2);
  const hasBox = form.box && Number.isFinite(lat2) && Number.isFinite(lon2);
  return (
    <MapContainer center={[lat || 20, lon || 78]} zoom={5} className="map" scrollWheelZoom>
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Clicks onPick={onPick} />
      <Fly lat={lat} lon={lon} />
      {Number.isFinite(lat) && Number.isFinite(lon) && <Marker position={[lat, lon]} icon={icon} />}
      {hasBox && <Rectangle bounds={[[lat, lon], [lat2, lon2]]} pathOptions={{ color: "#e35336" }} />}
    </MapContainer>
  );
}
