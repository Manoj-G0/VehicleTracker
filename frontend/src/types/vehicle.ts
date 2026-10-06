export type VehicleFilters = {
  base_model_name?: string;
  rlf_id?: string;
  rm_id?: string;
  ip_id?: string;
  rm_rlf_band?: string;
  ip_band?: string;
  evap_id?: string;
  pr_id?: string;
  df_id?: string;
  ob_id?: string;
  er_id?: string;
  pems_id?: string;
  variant_name?: string;
  page?: number;
  page_size?: number;
};

export type Variant = {
  id: number;
  variant_name: string;
  equation?: string | null;
  cycle_energy_demand?: string | null;
  co2?: string | null;
};

export type VehicleListItem = {
  id: number;
  base_model_name: string;
  rlf_id: string | null;
  rm_id: string | null;
  ip_id: string | null;
  rm_rlf_band: string | null;
  ip_band: string | null;
  evap_id: string | null;
  pr_id: string | null;
  df_id: string | null;
  ob_id: string | null;
  er_id: string | null;
  pems_id: string | null;
  variant_count: number;
  created_at?: string | null;
  updated_at?: string | null;
};

export type VehicleDetail = Omit<VehicleListItem, "variant_count"> & {
  variants: Variant[];
  created_at: string;
  updated_at: string;
};

export type VehicleWritePayload = {
  base_model_name: string;
  rlf_id: string | null;
  rm_id: string | null;
  ip_id: string | null;
  rm_rlf_band: string | null;
  ip_band: string | null;
  evap_id: string | null;
  pr_id: string | null;
  df_id: string | null;
  ob_id: string | null;
  er_id: string | null;
  pems_id: string | null;
  variants: {
    variant_name: string;
    equation?: string | null;
    cycle_energy_demand?: string | null;
    co2?: string | null;
  }[];
};

export type VehiclePage = {
  items: VehicleListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};
