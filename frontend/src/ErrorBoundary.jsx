import { Component } from "react";
import { reportError } from "./logger.js";

// Shows a fallback instead of a blank page when a component throws. Sits outside the layout, so it styles itself.
export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    reportError("render-error", error?.message, `${error?.stack || ""}\n${info.componentStack || ""}`);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 16 }}>
        <div className="card state--error" role="alert" style={{ maxWidth: 440, textAlign: "center" }}>
          <h3 style={{ justifyContent: "center", color: "inherit" }}>Something went wrong</h3>
          <p style={{ margin: "0 0 16px", fontSize: 14 }}>The page hit an unexpected error. Reloading usually fixes it.</p>
          <button type="button" className="btn btn--primary" onClick={() => window.location.reload()}>
            Reload
          </button>
        </div>
      </div>
    );
  }
}
