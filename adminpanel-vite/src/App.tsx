import { useEffect, useState, useCallback } from "react";
import { FiRefreshCw, FiAlertTriangle, FiInbox } from "react-icons/fi";
import { useTelegram } from "./hooks/useTelegram";
import { useApi } from "./hooks/useApi";
import type { TabType } from "./types";
import { StatsGrid } from "./components/StatsGrid";
import { TabNavigation } from "./components/TabNavigation";
import { PaymentCard } from "./components/PaymentCard";
import { RejectModal } from "./components/RejectModal";
import { BulkActionBar } from "./components/BulkActionBar";

function Spinner() {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-slate-400">
      <FiRefreshCw className="animate-spin text-indigo-400 text-3xl" />
      <span className="text-sm font-medium">Yuklanmoqda...</span>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-2 text-slate-500">
      <FiInbox className="text-4xl text-slate-600" />
      <p className="text-sm font-medium">Ma'lumotlar topilmadi</p>
    </div>
  );
}

function App() {
  const { adminId, expand, triggerHaptic } = useTelegram();
  const { stats, payments, loading, error, fetchStats, fetchPayments, actionPayment } =
    useApi(adminId);

  const [activeTab, setActiveTab] = useState<TabType>("stats");
  const [submitting, setSubmitting] = useState(false);
  const [rejectModal, setRejectModal] = useState<{
    isOpen: boolean;
    paymentId: number | null;
  }>({ isOpen: false, paymentId: null });
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
    if (activeTab !== "stats") await fetchPayments(activeTab);
  }, [fetchStats, fetchPayments, activeTab]);

  const handleApprove = useCallback(
    async (id: number) => {
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
    },
    [actionPayment, triggerHaptic, refreshAll]
  );

  const handleReject = useCallback(
    async (id: number, note: string) => {
      setSubmitting(true);
      triggerHaptic("warning");
      try {
        if (id === -1) {
          // Bulk reject
          await Promise.all(selectedIds.map((x) => actionPayment(x, "rejected", note)));
          setSelectedIds([]);
        } else {
          await actionPayment(id, "rejected", note);
        }
        setRejectModal({ isOpen: false, paymentId: null });
        await refreshAll();
      } catch {
        triggerHaptic("error");
      } finally {
        setSubmitting(false);
      }
    },
    [actionPayment, triggerHaptic, refreshAll, selectedIds]
  );

  const handleBulkApprove = useCallback(async () => {
    setSubmitting(true);
    triggerHaptic("success");
    try {
      await Promise.all(selectedIds.map((id) => actionPayment(id, "paid")));
      setSelectedIds([]);
      await refreshAll();
    } catch {
      triggerHaptic("error");
    } finally {
      setSubmitting(false);
    }
  }, [actionPayment, selectedIds, triggerHaptic, refreshAll]);

  const handleBulkReject = useCallback(() => {
    setRejectModal({ isOpen: true, paymentId: -1 }); // -1 indicates bulk reject
  }, []);

  const openRejectModal = useCallback((id: number) => {
    setRejectModal({ isOpen: true, paymentId: id });
  }, []);

  const closeRejectModal = useCallback(() => {
    setRejectModal({ isOpen: false, paymentId: null });
  }, []);

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
          onChange={setActiveTab}
          pendingCount={stats?.pending_pays ?? 0}
        />
      </div>

      {/* Main content */}
      <div className="max-w-xl mx-auto px-4 pt-4 pb-20">
        {/* Error banner */}
        {error && (
          <div className="mb-4 px-4 py-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs flex items-center gap-2">
            <FiAlertTriangle className="shrink-0" />
            Xatolik: {error}
          </div>
        )}

        {/* Stats tab */}
        {activeTab === "stats" && <StatsGrid stats={stats} loading={loading} />}

        {/* Payment tabs */}
        {activeTab !== "stats" && (
          <>
            {loading ? (
              <Spinner />
            ) : payments.length === 0 ? (
              <EmptyState />
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

      {/* Bulk action bar */}
      <BulkActionBar
        selectedCount={selectedIds.length}
        onBulkApprove={handleBulkApprove}
        onBulkReject={handleBulkReject}
        submitting={submitting}
      />

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
