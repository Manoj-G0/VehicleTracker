export function displayId(value: string | null | undefined): string {
  return value && value.trim() ? value : "--";
}

export function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export const FILTER_FIELDS = [
  { name: "base_model_name", label: "Base Model Name" },
  { name: "rlf_id", label: "RLF ID" },
  { name: "rm_id", label: "RM ID" },
  { name: "ip_id", label: "IP ID" },
  { name: "evap_id", label: "EVAP ID" },
  { name: "pr_id", label: "PR ID" },
  { name: "df_id", label: "DF ID" },
  { name: "ob_id", label: "OB ID" },
  { name: "er_id", label: "ER ID" },
  { name: "pems_id", label: "PEMS ID" },
  { name: "variant_name", label: "Variant Name" },
] as const;

export type FilterFieldName = (typeof FILTER_FIELDS)[number]["name"];
