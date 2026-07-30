import { useEffect, useState, useCallback, useMemo } from "react";
import { FiSearch } from "react-icons/fi";
import { useTelegram } from "./hooks/useTelegram";
import type { Stats, PaymentRequest } from "./types";
import { StatsGrid } from "./components/StatsGrid";
import { TabNavigation } from "./components/TabNavigation";
import { PaymentCard } from "./components/PaymentCard";
import { BulkActionBar } from "./components/BulkActionBar";
import { RejectModal } from "./components/RejectModal";

function App() {
  const { adminId, triggerHaptic } = useTelegram();

  const [stats, setStats] = useState<Stats | null>(null);
  const [payments, setPayments] = useState<PaymentRequest[]>([]);
  const [activeTab, setActiveTab] = useState<"pending" | "paid" | "rejected" >("pending");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedId, setCopiedId] = useState<number | null>(null);

  // Rejection states
  const [rejectId, setRejectId] = useState<number | null>(null);
  const [bulkRejectOpen, setBulkRejectOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const getApiUrl = (path: string) => {
    const host = window.location.port === "5173" ? "http://localhost:8000" : "";
    return `${host}${path}`;
  };

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const statsRes = await fetch(getApiUrl(`/api/stats?admin_id=${adminId}`));
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      const paymentsRes = await fetch(
        getApiUrl(`/api/payments?admin_id=${adminId}&status=${activeTab}`)
      );
      if (paymentsRes.ok) {
        const paymentsData = await paymentsRes.json();
        setPayments(paymentsData);
      }
    } catch (error) {
      console.error("Xatolik:", error);
    } finally {
      setLoading(false);
    }
  }, [adminId, activeTab]);

  useEffect(() => {
    setSelectedIds([]);
    fetchData();
  }, [fetchData]);

  // Action Callback
  const handleAction = useCallback(async (id: number, action: "paid" | "rejected", note = "") => {
    setSubmitting(true);
    triggerHaptic(action === "paid" ? "success" : "warning");
    try {
      const res = await fetch(getApiUrl("/api/payments/action"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          admin_id: adminId,
          id,
          action,
          note,
        }),
      });

      if (res.ok) {
        setRejectId(null);
        fetchData();
      } else {
        alert("Xatolik yuz berdi.");
      }
    } catch (error) {
      console.error(error);
    } finally {
      setSubmitting(false);
    }
  }, [adminId, fetchData, triggerHaptic]);

  // Bulk Operations Callbacks
  const handleBulkPay = useCallback(async () => {
    setSubmitting(true);
    triggerHaptic("success");
    try {
      await Promise.all(
        selectedIds.map((id) =>
          fetch(getApiUrl("/api/payments/action"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              admin_id: adminId,
              id,
              action: "paid",
            }),
          })
        )
      );
      setSelectedIds([]);
      fetchData();
    } catch (error) {
      console.error("Ommaviy to'lovda xato:", error);
    } finally {
      setSubmitting(false);
    }
  }, [adminId, selectedIds, fetchData, triggerHaptic]);

  const handleBulkRejectSubmit = useCallback(async (note: string) => {
    setSubmitting(true);
    triggerHaptic("warning");
    try {
      await Promise.all(
        selectedIds.map((id) =>
          fetch(getApiUrl("/api/payments/action"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              admin_id: adminId,
              id,
              action: "rejected",
              note,
            }),
          })
        )
      );
      setBulkRejectOpen(false);
      setSelectedIds([]);
      fetchData();
    } catch (error) {
      console.error("Ommaviy rad etishda xato:", error);
    } finally {
      setSubmitting(false);
    }
  }, [adminId, selectedIds, fetchData, triggerHaptic]);

  // Copy Callback
  const copyToClipboard = useCallback((text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    triggerHaptic("light");
    setTimeout(() => {
      setCopiedId((prev) => (prev === id ? null : prev));
    }, 10000);
  }, [triggerHaptic]);

  // Search logic and filtering memoization
  const filteredPayments = useMemo(() => {
    const query = searchQuery.toLowerCase();
    return payments.filter((p) => {
      return (
        p.card_number.includes(query) ||
        p.phone.includes(query) ||
        p.full_name.toLowerCase().includes(query) ||
        (p.username && p.username.toLowerCase().includes(query))
      );
    });
  }, [payments, searchQuery]);

  const handleSelectAll = useCallback(() => {
    if (selectedIds.length === filteredPayments.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredPayments.map((p) => p.id));
    }
  }, [selectedIds, filteredPayments]);

  const handleSelectChange = useCallback((id: number, checked: boolean) => {
    if (checked) {
      setSelectedIds((prev) => [...prev, id]);
    } else {
      setSelectedIds((prev) => prev.filter((item) => item !== id));
    }
  }, []);

  const onPayClick = useCallback((id: number) => {
    handleAction(id, "paid");
  }, [handleAction]);

  const onRejectClick = useCallback((id: number) => {
    setRejectId(id);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-4 max-w-xl mx-auto pb-24">
      {/* Sticky Header and Controls */}
      <div className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md pb-4 border-b border-slate-800 mb-4">
        <header className="flex justify-between items-center mb-4 pt-2">
          <h1 className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            OpenBudget Admin
          </h1>
          <p className="text-xs text-slate-400">
            ID: <code className="bg-slate-800 px-1.5 py-0.5 rounded font-mono text-indigo-300">{adminId}</code>
          </p>
        </header>

        {stats && <StatsGrid stats={stats} />}

        <TabNavigation
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          pendingCount={stats?.pending_pays || 0}
        />

        <div className="flex gap-2 items-center">
          <div className="relative flex items-center flex-1">
            <FiSearch className="absolute left-3.5 text-slate-500 text-base" />
            <input
              type="text"
              placeholder="Qidiruv (Ism, tel, karta)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-100 text-sm focus:border-indigo-500 focus:outline-none transition-all"
            />
          </div>
          {activeTab === "pending" && filteredPayments.length > 0 && (
            <button
              onClick={handleSelectAll}
              className="text-[11px] font-bold px-3 py-2.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 rounded-xl text-slate-300 transition-colors whitespace-nowrap cursor-pointer"
            >
              {selectedIds.length === filteredPayments.length ? "Bekor qilish" : "Barchasi"}
            </button>
          )}
        </div>
      </div>

      {/* Content Area */}
      {loading ? (
        <div className="text-center py-12 text-slate-400 font-medium">Yuklanmoqda...</div>
      ) : (
        <div className="flex flex-col gap-3">
          {filteredPayments.length === 0 ? (
            <div className="text-center py-12 text-slate-400 font-medium bg-slate-900 border border-slate-800 rounded-2xl">
              Ma'lumotlar topilmadi.
            </div>
          ) : (
            filteredPayments.map((p) => (
              <PaymentCard
                key={p.id}
                payment={p}
                activeTab={activeTab}
                isSelected={selectedIds.includes(p.id)}
                onSelectChange={handleSelectChange}
                copiedId={copiedId}
                onCopyClick={copyToClipboard}
                onPayClick={onPayClick}
                onRejectClick={onRejectClick}
              />
            ))
          )}
        </div>
      )}

      {/* Rejection Modals */}
      <RejectModal
        isOpen={rejectId !== null}
        onClose={() => setRejectId(null)}
        onSubmit={(note) => handleAction(rejectId!, "rejected", note)}
        submitting={submitting}
        title="Rad etish sababi"
      />

      <RejectModal
        isOpen={bulkRejectOpen}
        onClose={() => setBulkRejectOpen(false)}
        onSubmit={handleBulkRejectSubmit}
        submitting={submitting}
        title="Ommaviy rad etish sababi"
      />

      {/* Floating Bottom Bar for Bulk Operations */}
      <BulkActionBar
        selectedCount={selectedIds.length}
        onBulkPay={handleBulkPay}
        onBulkReject={() => setBulkRejectOpen(true)}
        submitting={submitting}
      />
    </div>
  );
}

export default App;
