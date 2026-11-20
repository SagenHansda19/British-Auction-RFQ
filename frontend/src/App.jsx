import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, Route, Routes } from "react-router-dom";

import { api, getUserId, setUserId } from "./api";
import CreateRfq from "./pages/CreateRfq";
import RfqDetail from "./pages/RfqDetail";
import RfqList from "./pages/RfqList";

export default function App() {
  const [userId, setUserIdState] = useState(getUserId());
  const { data: users = [] } = useQuery({ queryKey: ["users"], queryFn: api.getUsers });
  const currentUser = users.find((u) => String(u.id) === userId);

  function switchUser(id) {
    setUserId(id);
    setUserIdState(id);
  }

  return (
    <div className="min-h-screen">
      <header className="bg-slate-900 text-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <nav className="flex items-center gap-6">
            <Link to="/" className="text-lg font-semibold">British Auction RFQ</Link>
            <Link to="/" className="text-slate-300 hover:text-white">Auctions</Link>
            {currentUser?.role === "BUYER" && (
              <Link to="/rfqs/new" className="text-slate-300 hover:text-white">Create RFQ</Link>
            )}
          </nav>
          <label className="flex items-center gap-2 text-sm">
            <span className="text-slate-300">Acting as</span>
            <select
              value={userId || ""}
              onChange={(e) => switchUser(e.target.value)}
              className="rounded bg-slate-800 px-2 py-1 text-white"
            >
              <option value="" disabled>Select a user</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name} ({u.role === "BUYER" ? "Buyer" : "Supplier"})
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        {!currentUser && (
          <p className="mb-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm">
            Choose a user in the top-right corner. Buyers create RFQs, suppliers place bids.
          </p>
        )}
        <Routes>
          <Route path="/" element={<RfqList />} />
          <Route path="/rfqs/new" element={<CreateRfq currentUser={currentUser} />} />
          <Route path="/rfqs/:id" element={<RfqDetail currentUser={currentUser} />} />
        </Routes>
      </main>
    </div>
  );
}
