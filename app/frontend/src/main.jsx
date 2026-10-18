import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import { VoiceSettingsProvider } from "./voice/VoiceSettings";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <VoiceSettingsProvider>
      <App />
    </VoiceSettingsProvider>
  </React.StrictMode>
);
