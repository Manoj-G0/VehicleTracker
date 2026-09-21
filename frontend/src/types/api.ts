export type ApiFieldError = {
  field: string;
  message: string;
};

export type ImportIssue = {
  row: number | null;
  field: string | null;
  message: string;
};

export type ImportPreview = {
  file_name: string;
  total_rows: number;
  base_models_detected: number;
  variants_detected: number;
  new_vehicles: number;
  existing_vehicles: number;
  new_variants: number;
  duplicate_variants: number;
  warnings: ImportIssue[];
  errors: ImportIssue[];
  can_import: boolean;
};

export type ImportResult = {
  file_name: string;
  mode: "upsert" | "replace";
  total_rows: number;
  created_vehicles: number;
  updated_vehicles: number;
  created_variants: number;
  skipped_variants: number;
  warnings: ImportIssue[];
  errors: ImportIssue[];
  job_id: number | null;
};

export type ImportMode = "upsert" | "replace";

export class ApiError extends Error {
  status: number;
  detail: string;
  fields: ApiFieldError[];

  constructor(status: number, detail: string, fields: ApiFieldError[] = []) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.fields = fields;
  }
}
