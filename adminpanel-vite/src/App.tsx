import { useEffect, useState, useCallback } from "react";
import { useTelegram } from "./hooks/useTelegram";
import { useApi } from "./hooks/useApi";
import type { TabType } from "./types";
import { StatsGrid } from "./components/StatsGrid";
import { TabNavigation } from "./components/TabNavigation";
import { PaymentCard } from "./components/PaymentCard";
import { RejectModal } from "./components/RejectModal";

function App() {
  const { adminId, expand, triggerHaptic } = useTelegram();
  const { stats, payments, loading, error, fetchStats, fetchPayments, actionPayment } = useApi(adminId);

  const [activeTab, setActiveTab] = useState<TabType>("stats");
  const [submitting, setSubmitting] = useState(false);
  const [rejectModal, setRejectModal] = useState<{ isOpen: boolean; paymentId: number | null }>({
    isOpen: false,
    paymentId: null,
  });
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  // Expand webapp on mount and load initial data
  useEffect(() => {
    expand();
    fetchStats();
    fetchPayments("pending");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reload data when tab changes
  useEffect(() => {
    if (activeTab === "stats") {
      fetchStats();
    } else {
      fetchPayments(activeTab);
      setSelectedIds([]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const refreshAll = useCallback(async () => {
    await fetchStats();
    if (activeTab !== "stats") {
      await fetchPayments(activeTab);
    }
  }, [fetchStats, fetchPayments, activeTab]);

  const handleApprove = useCallback(async (id: number) => {
    setSubmitting(true);
    triggerHaptic("success");
    try {
      await actionPayment(id, "paid");
      await refreshAll();
    } catch {
      triggerHaptic("error");
    } finally {
      setSubmitting(false);
    }
  }, [actionPayment, triggerHaptic, refreshAll]);

  const handleReject = useCallback(async (id: number, note: string) => {
    setSubmitting(true);
    triggerHaptic("warning");
    try {
      await actionPayment(id, "rejected", note);
      setRejectModal({ isOpen: false, paymentId: null });
      await refreshAll();
    } catch {
      triggerHaptic("error");
    } finally {
      setSubmitting(false);
    }
  }, [actionPayment, triggerHaptic, refreshAll]);

  const openRejectModal = useCallback((id: number) => {
    setRejectModal({ isOpen: true, paymentId: id });
  }, []);

  const closeRejectModal = useCallback(() => {
    setRejectModal({ isOpen: false, paymentId: null });
  }, []);

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-slate-100 font-sans pb-8">
      {/* Sticky header — L2 elevation */}
      <div className="sticky top-0 z-40 bg-slate-800/90 backdrop-blur-md shadow-md border-b border-slate-700/40 px-4 pt-3 pb-3">
        <header className="flex justify-between items-center mb-3">
          <h1 className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            OpenBudget Admin
          </h1>
          <p className="text-xs text-slate-400">
            ID:{" "}
            <code className="bg-slate-800 px-1.5 py-0.5 rounded font-mono text-indigo-300">
              {adminId ?? "—"}
            </code>
          </p>
        </header>

        <TabNavigation
          activeTab={activeTab}
          onChange={handleTabChange}
          pendingCount={stats?.pending_pays ?? 0}
        />
      </div>

      {/* Main content */}
      <div className="max-w-xl mx-auto px-4 pt-4">
        {/* Error banner */}
        {error && (
          <div className="mb-4 px-4 py-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs">
            ⚠️ Xatolik: {error}
          </div>
        )}

        {/* Stats tab */}
        {activeTab === "stats" && (
          <StatsGrid stats={stats} loading={loading} />
        )}

        {/* Payment tabs */}
        {activeTab !== "stats" && (
          <>
            {loading ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3 text-slate-400">
                <svg className="animate-spin h-8 w-8 text-indigo-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span className="text-sm font-medium">Yuklanmoqda...</span>
              </div>
            ) : payments.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-2 text-slate-500">
                <span className="text-4xl">📭</span>
                <p className="text-sm font-medium">Ma'lumotlar topilmadi</p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {payments.map((p) => (
                  <PaymentCard
                    key={p.id}
                    payment={p}
                    onApprove={handleApprove}
                    onReject={handleReject}
                    onRejectPrompt={openRejectModal}
                    disabled={submitting}
                    isSelected={selectedIds.includes(p.id)}
                    onSelect={(id, checked) =>
                      setSelectedIds((prev) =>
                        checked ? [...prev, id] : prev.filter((x) => x !== id)
                      )
                    }
                    activeTab={activeTab}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Reject Modal */}
      <RejectModal
        isOpen={rejectModal.isOpen}
        paymentId={rejectModal.paymentId}
        onConfirm={handleReject}
        onClose={closeRejectModal}
      />
    </div>
  );
}

export default App;
