import { BrowserRouter, Routes, Route } from "react-router-dom";
import { RuntimeProvider } from "@/providers/runtime-provider";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { DashboardPage } from "@/pages/dashboard-page";
import { ChatPage } from "@/pages/chat-page";
import { PortfolioPage } from "@/pages/portfolio-page";
import { FilingsPage } from "@/pages/filings-page";
import { NewsPage } from "@/pages/news-page";
import { SettingsPage } from "@/pages/settings-page";

function App() {
  return (
    <BrowserRouter>
      <RuntimeProvider>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="portfolio" element={<PortfolioPage />} />
            <Route path="filings" element={<FilingsPage />} />
            <Route path="news" element={<NewsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </RuntimeProvider>
    </BrowserRouter>
  );
}

export default App;
