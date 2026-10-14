import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout.jsx";
import About from "./pages/About.jsx";
import Analyzer from "./pages/Analyzer.jsx";
import Method from "./pages/Method.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Analyzer />} />
          <Route path="/method" element={<Method />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<Analyzer />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
