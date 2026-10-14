export default function ToggleSwitch({ checked, onChange, label }) {
  return (
    <label className="toggle-switch">
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span className="toggle-switch-track">
        <span className="toggle-switch-thumb" />
      </span>
      {label && <span>{label}</span>}
    </label>
  );
}
