import React from "react";
import { createRoot } from "react-dom/client";
import "leaflet/dist/leaflet.css";
import "./theme.css";
import "./index.css";
import "./App.css";
import App from "./App.jsx";
import ErrorBoundary from "./ErrorBoundary.jsx";
import { installGlobalHandlers } from "./logger.js";

installGlobalHandlers();
createRoot(document.getElementById("root")).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>,
);
