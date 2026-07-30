import { useState, useCallback } from "react";
import type { Stats, Payment } from "../types";

const getApiBase = () =>
  window.location.port === "5173" ? "http://localhost:8000" : "";

export function useApi(adminId: number | null) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const base = getApiBase();

  const fetchStats = useCallback(async () => {
    if (!adminId) return;
    try {
      const res = await fetch(`${base}/api/stats?admin_id=${adminId}`);
      if (!res.ok) throw new Error(`Stats fetch failed: ${res.status}`);
      const data: Stats = await res.json();
      setStats(data);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [adminId, base]);

  const fetchPayments = useCallback(
    async (status?: string) => {
      if (!adminId) return;
      setLoading(true);
      setError(null);
      try {
        const url = status
          ? `${base}/api/payments?admin_id=${adminId}&status=${status}`
          : `${base}/api/payments?admin_id=${adminId}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`Payments fetch failed: ${res.status}`);
        const data: Payment[] = await res.json();
        setPayments(data);
      } catch (e) {
        setError((e as Error).message);
        setPayments([]);
      } finally {
        setLoading(false);
      }
    },
    [adminId, base]
  );

  const actionPayment = useCallback(
    async (id: number, action: "paid" | "rejected", note = "") => {
      if (!adminId) return;
      const res = await fetch(`${base}/api/payments/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ admin_id: adminId, id, action, note }),
      });
      if (!res.ok) throw new Error(`Action failed: ${res.status}`);
      return res.json();
    },
    [adminId, base]
  );

  return {
    stats,
    payments,
    loading,
    error,
    fetchStats,
    fetchPayments,
    actionPayment,
  };
}
