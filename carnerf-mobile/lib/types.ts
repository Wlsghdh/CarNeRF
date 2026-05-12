export type Role = 'buyer' | 'seller';
export type ListingStatus = 'active' | 'reserved' | 'sold';
export type Model3DStatus = 'none' | 'processing' | 'ready';
export type Rating = 1 | 2 | 3 | 4 | 5;
export type ReviewType = 'buyer' | 'seller';
export type PointTxType = 'charge' | 'ai_usage' | 'premium_listing' | 'refund';
export type DeviceType = 'mobile' | 'desktop' | 'tablet';
export type Quality = 'standard' | 'hq' | 'ultra';

export interface User {
  id: number;
  email: string;
  username: string;
  phone?: string;
  role: Role;
  points: number;
  is_verified: boolean;
  region?: string;
  created_at: string;
}

export interface Vehicle {
  id: number;
  brand: string;
  model: string;
  year: number;
  trim?: string;
  fuel_type: string;
  transmission: string;
  mileage: number;
  color?: string;
  engine_cc?: number;
  region?: string;
  thumbnail_url?: string;
  model_3d_url?: string;
  model_3d_status: Model3DStatus;
}

export interface Listing {
  id: number;
  vehicle_id: number;
  seller_id: number;
  title: string;
  description?: string;
  price: number;
  is_negotiable: boolean;
  status: ListingStatus;
  view_count: number;
  created_at: string;
  vehicle?: Vehicle;
  seller?: User;
}

export interface DiagnosisReport {
  id: number;
  vehicle_id: number;
  overall_score: number;
  exterior_score: number;
  interior_score: number;
  engine_score: number;
  accident_history: number;
  estimated_price_low: number;
  estimated_price_high: number;
  report_summary: string;
}

export interface PointTransaction {
  id: number;
  user_id: number;
  amount: number;
  balance_after: number;
  transaction_type: PointTxType;
  description: string;
  created_at: string;
}

export interface UserReview {
  id: number;
  vehicle_id: number;
  author_id: number;
  rating: Rating;
  content: string;
  review_type: ReviewType;
  created_at: string;
}

export interface Wishlist {
  user_id: number;
  vehicle_id: number;
  created_at: string;
}

export interface TransactionHistory {
  id: number;
  vehicle_id: number;
  transaction_date: string;
  price: number;
  mileage_at_sale: number;
  source: 'carnerf' | 'external';
  buyer_region?: string;
  seller_region?: string;
}

export interface LoginHistory {
  id: number;
  user_id: number;
  ip_address: string;
  user_agent: string;
  device_type: DeviceType;
  location?: string;
  success: boolean;
  created_at: string;
}

export interface VehicleSummary {
  summary: string;
  pros: string[];
  cons: string[];
  known_issues: string[];
  review_summary?: string;
}

export interface DefectInfo {
  bbox: [number, number, number, number];
  type: string;
  severity: 'low' | 'medium' | 'high';
  confidence: number;
  position_3d?: [number, number, number];
}

export interface DefectReport {
  total_defect_score: number;
  severity_level: 'low' | 'medium' | 'high';
  defects: DefectInfo[];
}

export interface PriceEstimate {
  predicted_price: number;
  price_range_low: number;
  price_range_high: number;
  confidence: number;
  depreciation_curve: { year: number; price: number }[];
}

export interface MarketPrice {
  internal_average: number;
  external_average?: number;
  depreciation_estimate: number;
}

export interface AIRecommendResult {
  parsed_filters: Record<string, any>;
  listings: (Listing & { match_score: number })[];
  relax_level: number;
}

export interface PipelineStatus {
  job_id: string;
  status:
    | 'queued'
    | 'extracting_frames'
    | 'colmap'
    | 'removing_background'
    | 'generating_depth'
    | 'training'
    | 'exporting'
    | 'completed'
    | 'failed';
  progress: number;
  message?: string;
  model_url?: string;
}
