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

export interface PaymentRequest {
  id: number;
  tg_id: number;
  phone: string;
  full_name: string;
  card_number: string;
  amount: number;
  status: string;
  requested_at: string;
  username?: string;
  u_full_name?: string;
}
