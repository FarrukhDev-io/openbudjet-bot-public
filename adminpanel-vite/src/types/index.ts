export interface Stats {
  total_users: number;
  total_votes: number;
  confirmed: number;
  today_votes: number;
  total_refs: number;
  pending_pays: number;
  paid_count: number;
  total_paid_sum: number;
}

export interface Payment {
  id: number;
  tg_id: number;
  phone: string;
  full_name: string;
  card_number: string;
  amount: number;
  status: "pending" | "paid" | "rejected";
  requested_at: string;
  processed_at: string | null;
  admin_note: string | null;
  username: string | null;
}

export type TabType = "stats" | "pending" | "paid" | "rejected";
