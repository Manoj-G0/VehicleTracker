"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { VehicleDetail, VehicleFilters, VehiclePage } from "@/types/vehicle";
import type { ImportPreview, ImportResult } from "@/types/api";
import { identifierLabels, labels } from "@/config/labels";
import { CarFront, Download, LogOut, Pencil, Plus, RotateCcw, Search, Trash2, Upload, UserRound, Users } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

type AuthUser = {
  id: number;
  username: string;
  email: string;
  role: "ADMIN" | "USER";
  allow_access: boolean;
  is_active: boolean;
};

type StoredAuth = { token: string; refreshToken: string; user: AuthUser };
type VariantDraft = { variant_name: string; equation: string; cycle_energy_demand: string; co2: string };
type VehicleForm = {
  base_model_name: string;
  rlf_id: string;
  rm_id: string;
  rm_rlf_band: string;
  ip_id: string;
  ip_band: string;
  evap_id: string;
  pr_id: string;
  df_id: string;
  ob_id: string;
  er_id: string;
  pems_id: string;
  variants: VariantDraft[];
};

const EMPTY_VARIANT_DRAFT: VariantDraft = {
  variant_name: "",
  equation: "",
  cycle_energy_demand: "",
  co2: "",
};

type FilterField = {
  key: keyof VehicleFilters;
  label: string;
};

const FILTER_FIELDS: FilterField[] = [
  { key: "base_model_name", label: labels.vehicle.baseModelName },
  ...Object.entries(identifierLabels).map(([key, label]) => ({ key: key as keyof VehicleFilters, label })),
  { key: "variant_name", label: labels.vehicle.variantName },
];

const EMPTY_VEHICLE_FORM = {
  base_model_name: "",
  rlf_id: "",
  rm_id: "",
  rm_rlf_band: "",
  ip_id: "",
  ip_band: "",
  evap_id: "",
  pr_id: "",
  df_id: "",
  ob_id: "",
  er_id: "",
  pems_id: "",
  variants: [],
};

async function api<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers ?? {});
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = "Something went wrong.";
    try {
      const payload = await response.json();
      if (payload?.detail) {
        if (Array.isArray(payload.detail)) {
          message = String(payload.detail[0]?.message ?? payload.detail[0] ?? message);
        } else {
          message = String(payload.detail);
        }
      }
    } catch {
      void 0;
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function readStoredAuth(): StoredAuth | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem("vehicle_tracker_auth");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredAuth;
  } catch {
    return null;
  }
}

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [view, setView] = useState<"search" | "add" | "upload" | "profile" | "users">("search");
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [registrationForm, setRegistrationForm] = useState({ username: "", email: "", password: "" });
  const [authMode, setAuthMode] = useState<"login" | "register" | "forgot" | "verify-registration" | "verify-reset" | "set-reset-password">("login");
  const [loginError, setLoginError] = useState("");
  const [filters, setFilters] = useState<VehicleFilters>({});
  const [page, setPage] = useState(1);
  const [searchError, setSearchError] = useState("");
  const [results, setResults] = useState<VehiclePage | null>(null);
  const [selected, setSelected] = useState<VehicleDetail | null>(null);
  const [variantItems, setVariantItems] = useState<VehicleDetail["variants"]>([]);
  const [variantPage, setVariantPage] = useState(1);
  const [variantTotalPages, setVariantTotalPages] = useState(0);
  const [variantLoading, setVariantLoading] = useState(false);
  const vehicleOpenRequest = useRef(0);
  const variantLoadRequest = useRef(0);
  const [vehicleForm, setVehicleForm] = useState<VehicleForm>(EMPTY_VEHICLE_FORM);
  const [editingVehicleId, setEditingVehicleId] = useState<number | null>(null);
  const [vehicleError, setVehicleError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<{ status: string; summary: string } | null>(null);
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [importMode, setImportMode] = useState<"upsert" | "replace">("upsert");
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [userForm, setUserForm] = useState({ username: "", email: "", role: "USER" });
  const [userError, setUserError] = useState("");
  const [passwordForm, setPasswordForm] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [passwordState, setPasswordState] = useState("");
  const [profile, setProfile] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(false);
  const [pendingRegistration, setPendingRegistration] = useState<{ username: string; email: string } | null>(null);
  const [forgotPasswordEmail, setForgotPasswordEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [resetForm, setResetForm] = useState({ otp: "", new_password: "", confirm_password: "" });
  const [registrationOtp, setRegistrationOtp] = useState("");
  const [resendSeconds, setResendSeconds] = useState(0);
  const [variantModalOpen, setVariantModalOpen] = useState(false);
  const [variantDraft, setVariantDraft] = useState<VariantDraft>(EMPTY_VARIANT_DRAFT);
  const [variantEditIndex, setVariantEditIndex] = useState<number | null>(null);
  const [variantEditId, setVariantEditId] = useState<number | null>(null);
  const [variantDialogMode, setVariantDialogMode] = useState<"vehicle" | "detail">("vehicle");

  const admin = user?.role === "ADMIN";

  const navItems = useMemo(() => {
    const items: { label: string; value: "search" | "add" | "upload" | "profile" | "users" | "logout" }[] = [{ label: labels.navigation.search, value: "search" }];
    if (admin) items.push({ label: labels.navigation.management, value: "add" });
    if (admin) items.push({ label: labels.navigation.upload, value: "upload" });
    if (admin) items.push({ label: labels.navigation.users, value: "users" });
    items.push({ label: labels.navigation.profile, value: "profile" });
    items.push({ label: labels.navigation.logout, value: "logout" });
    return items;
  }, [admin]);

  useEffect(() => {
    const saved = readStoredAuth();
    if (!saved) return;
    setToken(saved.token);
    setRefreshToken(saved.refreshToken);
    setUser(saved.user);
    void loadProfile(saved.token);
    void fetchVehicles(saved.token);
  }, []);

  useEffect(() => {
    if (resendSeconds <= 0) return;
    const timer = window.setInterval(() => setResendSeconds((remaining) => Math.max(remaining - 1, 0)), 1000);
    return () => window.clearInterval(timer);
  }, [resendSeconds > 0]);

  useEffect(() => {
    if (![loginError, searchError, vehicleError, userError, passwordState].some(Boolean)) return;
    const timer = window.setTimeout(() => {
      setLoginError("");
      setSearchError("");
      setVehicleError("");
      setUserError("");
      setPasswordState("");
    }, 6000);
    return () => window.clearTimeout(timer);
  }, [loginError, searchError, vehicleError, userError, passwordState]);

  useEffect(() => {
    if (!uploadState || uploadState.status === "Uploading..." || uploadState.status === labels.common.loading) return;
    const timer = window.setTimeout(() => setUploadState(null), 8000);
    return () => window.clearTimeout(timer);
  }, [uploadState]);

  async function loadProfile(currentToken: string) {
    try {
      const payload = await api<{ id: number; username: string; email: string; role: string; allow_access: boolean; is_active: boolean }>("/profile", { method: "GET" }, currentToken);
      setProfile({ ...payload, role: payload.role === "ADMIN" ? "ADMIN" : "USER" });
    } catch {
      void 0;
    }
  }

  async function fetchVehicles(currentToken = token, requestedPage = page, activeFilters = filters) {
    setLoading(true);
    setSearchError("");
    const query = new URLSearchParams();
    Object.entries(activeFilters).forEach(([key, value]) => {
      if (value !== undefined && value !== "") query.set(key, String(value));
    });
    query.set("page", String(requestedPage));
    query.set("page_size", "10");
    try {
      const response = await fetch(`${API_BASE}/vehicles?${query.toString()}`, {
        headers: currentToken ? { Authorization: `Bearer ${currentToken}` } : undefined,
      });
      if (!response.ok) throw new Error("Unable to load vehicles");
      const payload = (await response.json()) as VehiclePage;
      setResults(payload);
    } catch (reason) {
      setSearchError(reason instanceof Error ? reason.message : "Unable to load vehicles");
    } finally {
      setLoading(false);
    }
  }

  async function openVehicle(id: number) {
    if (!token) return;
    const requestId = ++vehicleOpenRequest.current;
    const variantRequestId = ++variantLoadRequest.current;
    setSelected(null);
    setVariantItems([]);
    setVariantPage(1);
    setVariantTotalPages(0);
    setVariantLoading(true);
    try {
      const payload = await api<VehicleDetail>(`/vehicles/${id}`, { method: "GET" }, token);
      if (requestId !== vehicleOpenRequest.current) return;
      setSelected(payload);
      await loadVariants(id, 1, false);
    } catch {
      if (requestId === vehicleOpenRequest.current) {
        setSearchError("Unable to load vehicle details");
      }
    } finally {
      if (requestId === vehicleOpenRequest.current && variantLoadRequest.current === variantRequestId) {
        setVariantLoading(false);
      }
    }
  }

  async function loadVariants(vehicleId: number, requestedPage: number, append: boolean) {
    if (!token) return;
    const requestId = ++variantLoadRequest.current;
    setVariantLoading(true);
    try {
      const payload = await api<{ items: VehicleDetail["variants"]; page: number; total_pages: number }>(
        `/vehicles/${vehicleId}/variants?page=${requestedPage}&page_size=20`, { method: "GET" }, token,
      );
      if (requestId !== variantLoadRequest.current) return;
      setVariantItems((current) => append ? [...current, ...payload.items] : payload.items);
      setVariantPage(payload.page);
      setVariantTotalPages(payload.total_pages);
    } finally {
      if (requestId === variantLoadRequest.current) {
        setVariantLoading(false);
      }
    }
  }

  async function handleLogin(event: React.FormEvent) {
    event.preventDefault();
    setLoginError("");
    try {
      const payload = await api<{ access_token: string; refresh_token: string; user: AuthUser }>("/auth/login", {
        method: "POST",
        body: JSON.stringify(loginForm),
      });
      setToken(payload.access_token);
      setRefreshToken(payload.refresh_token);
      setUser(payload.user);
      setProfile(payload.user);
      setPasswordState("");
      setSearchError("");
      setUserError("");
      window.localStorage.setItem("vehicle_tracker_auth", JSON.stringify({ token: payload.access_token, refreshToken: payload.refresh_token, user: payload.user }));
      await fetchVehicles(payload.access_token, 1);
      setView("search");
    } catch (reason) {
      setLoginError(reason instanceof Error ? reason.message : "Authentication failed");
    }
  }

  async function handleRegistration(event: React.FormEvent) {
    event.preventDefault();
    setLoginError("");
    try {
      const payload = await api<{ status: string; message: string; resend_after_seconds: number }>("/auth/register", { method: "POST", body: JSON.stringify(registrationForm) });
      setPendingRegistration({ username: registrationForm.username, email: registrationForm.email });
      setAuthMode("verify-registration");
      setRegistrationOtp("");
      setResendSeconds(payload.resend_after_seconds);
      setLoginError("Verification code sent to your email");
    } catch (reason) {
      setLoginError(reason instanceof Error ? reason.message : "Registration failed");
    }
  }

  async function handleVerifyRegistration(event: React.FormEvent) {
    event.preventDefault();
    if (!pendingRegistration) return;
    setLoginError("");
    try {
      await api("/auth/register/verify", {
        method: "POST",
        body: JSON.stringify({
          username: pendingRegistration.username,
          email: pendingRegistration.email,
          otp: registrationOtp,
        }),
      });
      setLoginError("Verification complete. Please sign in.");
      setAuthMode("login");
      setPendingRegistration(null);
      setRegistrationForm({ username: "", email: "", password: "" });
      setRegistrationOtp("");
      setResendSeconds(0);
      setLoginForm({ username: pendingRegistration.username, password: "" });
    } catch (reason) {
      setLoginError(reason instanceof Error ? reason.message : "OTP verification failed");
    }
  }

  async function resendRegistrationOtp() {
    if (!pendingRegistration || resendSeconds > 0) return;
    setLoginError("");
    try {
      const payload = await api<{ message: string; resend_after_seconds: number }>("/auth/register/resend", {
        method: "POST",
        body: JSON.stringify({ email: pendingRegistration.email }),
      });
      setResendSeconds(payload.resend_after_seconds);
      setLoginError(payload.message);
    } catch (reason) {
      setLoginError(reason instanceof Error ? reason.message : "Unable to resend verification code");
    }
  }

  async function handleForgotPassword(event: React.FormEvent) {
    event.preventDefault();
    setLoginError("");
    try {
      const payload = await api<{ message: string; resend_after_seconds: number }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: forgotPasswordEmail }),
      });
      setAuthMode("verify-reset");
      setResendSeconds(payload.resend_after_seconds);
      setLoginError("Reset code sent to your email.");
    } catch (reason) {
      setLoginError(reason instanceof Error ? reason.message : "Unable to request reset code");
    }
  }

  async function resendPasswordResetOtp() {
    if (resendSeconds > 0) return;
    setLoginError("");
    try {
      const payload = await api<{ message: string; resend_after_seconds: number }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: forgotPasswordEmail }),
      });
      setResendSeconds(payload.resend_after_seconds);
      setLoginError(payload.message);
    } catch (reason) {
      setLoginError(reason instanceof Error ? reason.message : "Unable to resend reset code");
    }
  }

  async function handleVerifyReset(event: React.FormEvent) {
    event.preventDefault();
    setLoginError("");
    try {
      const payload = await api<{ status: string; token: string; message: string }>("/auth/forgot-password/verify", {
        method: "POST",
        body: JSON.stringify({ email: forgotPasswordEmail, otp: resetForm.otp }),
      });
      setResetToken(payload.token);
      setAuthMode("set-reset-password");
      setLoginError("OTP verified. Set a new password.");
    } catch (reason) {
      setLoginError(reason instanceof Error ? reason.message : "OTP verification failed");
    }
  }

  async function handleResetPassword(event: React.FormEvent) {
    event.preventDefault();
    setLoginError("");
    try {
      await api("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({
          token: resetToken,
          new_password: resetForm.new_password,
          confirm_password: resetForm.confirm_password,
        }),
      });
      setAuthMode("login");
      setForgotPasswordEmail("");
      setResetToken("");
      setResetForm({ otp: "", new_password: "", confirm_password: "" });
      setResendSeconds(0);
      setLoginForm({ username: "", password: "" });
      setLoginError("Password updated successfully.");
    } catch (reason) {
      setLoginError(reason instanceof Error ? reason.message : "Unable to reset password");
    }
  }

  async function handleLogout() {
    window.localStorage.removeItem("vehicle_tracker_auth");
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    setProfile(null);
    setSelected(null);
    setView("search");
    setPasswordState("");
    setLoginError("");
    setSearchError("");
    setVehicleError("");
    setUserError("");
    setUploadState(null);
  }

  function updateFilter(field: keyof VehicleFilters, value: string) {
    setFilters((current) => ({ ...current, [field]: value }));
    setPage(1);
  }

  async function resetFilters() {
    setFilters({});
    setPage(1);
    await fetchVehicles(token ?? undefined, 1, {});
  }

  async function exportVehicles() {
    if (!token) return;
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== "") query.set(key, String(value));
    });
    const response = await fetch(`${API_BASE}/vehicles/export?${query.toString()}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw new Error("Unable to export vehicles");
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "vehicle_master_export.xlsx";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  function openNewVariant(mode: "vehicle" | "detail") {
    setVariantDialogMode(mode);
    setVariantDraft(EMPTY_VARIANT_DRAFT);
    setVariantEditIndex(null);
    setVariantEditId(null);
    setVariantModalOpen(true);
  }

  function editVehicleVariant(index: number) {
    const variant = vehicleForm.variants[index];
    setVariantDialogMode("vehicle");
    setVariantDraft({
      variant_name: variant.variant_name,
      equation: variant.equation ?? "",
      cycle_energy_demand: variant.cycle_energy_demand ?? "",
      co2: variant.co2 ?? "",
    });
    setVariantEditIndex(index);
    setVariantEditId(null);
    setVariantModalOpen(true);
  }

  function editDetailVariant(variant: VehicleDetail["variants"][number]) {
    setVariantDialogMode("detail");
    setVariantDraft({
      variant_name: variant.variant_name,
      equation: variant.equation ?? "",
      cycle_energy_demand: variant.cycle_energy_demand ?? "",
      co2: variant.co2 ?? "",
    });
    setVariantEditId(variant.id);
    setVariantEditIndex(null);
    setVariantModalOpen(true);
  }

  async function saveVariantDraft() {
    const payload = {
      variant_name: variantDraft.variant_name.trim(),
      equation: variantDraft.equation.trim() || null,
      cycle_energy_demand: variantDraft.cycle_energy_demand.trim() || null,
      co2: variantDraft.co2.trim() || null,
    };
    if (!payload.variant_name) {
      setVehicleError("Variant name is required.");
      return;
    }
    if (variantDialogMode === "detail") {
      if (!selected || !token) return;
      try {
        const savedVariant = await api<VehicleDetail["variants"][number]>(`/vehicles/${selected.id}/variants${variantEditId ? `/${variantEditId}` : ""}`, {
          method: variantEditId ? "PUT" : "POST",
          body: JSON.stringify(payload),
        }, token);
        setSelected((current) => current ? {
          ...current,
          variants: variantEditId
            ? current.variants.map((variant) => variant.id === savedVariant.id ? savedVariant : variant)
            : [...current.variants, savedVariant],
        } : current);
        await Promise.all([
          loadVariants(selected.id, 1, false),
          fetchVehicles(token),
        ]);
        setVariantModalOpen(false);
      } catch (reason) {
        setSearchError(reason instanceof Error ? reason.message : "Unable to save variant");
      }
      return;
    }
    const draftValue: VariantDraft = {
      variant_name: payload.variant_name,
      equation: payload.equation ?? "",
      cycle_energy_demand: payload.cycle_energy_demand ?? "",
      co2: payload.co2 ?? "",
    };
    setVehicleForm((current) => ({
      ...current,
      variants: variantEditIndex === null
        ? [...current.variants, draftValue]
        : current.variants.map((variant, index) => index === variantEditIndex ? draftValue : variant),
    }));
    setVariantModalOpen(false);
  }

  function removeVehicleVariant(index: number) {
    setVehicleForm((current) => ({
      ...current,
      variants: current.variants.filter((_, variantIndex) => variantIndex !== index),
    }));
  }

  async function removeDetailVariant(variantId: number) {
    if (!selected || !token || !window.confirm("Delete this variant?")) return;
    try {
      await api(`/vehicles/${selected.id}/variants/${variantId}`, { method: "DELETE" }, token);
      setSelected((current) => current ? {
        ...current,
        variants: current.variants.filter((variant) => variant.id !== variantId),
      } : current);
      await Promise.all([
        loadVariants(selected.id, 1, false),
        fetchVehicles(token),
      ]);
    } catch (reason) {
      setSearchError(reason instanceof Error ? reason.message : "Unable to delete variant");
    }
  }

  async function saveVehicle(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setVehicleError("");
    try {
      const payload = {
        ...vehicleForm,
        variants: vehicleForm.variants.filter((variant) => variant.variant_name.trim()).map((variant) => ({
          variant_name: variant.variant_name.trim(),
          equation: variant.equation.trim() || null,
          cycle_energy_demand: variant.cycle_energy_demand.trim() || null,
          co2: variant.co2.trim() || null,
        })),
      };
      await api(editingVehicleId ? `/vehicles/${editingVehicleId}` : "/vehicles", {
        method: editingVehicleId ? "PUT" : "POST",
        body: JSON.stringify(payload),
      }, token);
      setVehicleForm(EMPTY_VEHICLE_FORM);
      setEditingVehicleId(null);
      setView("search");
      await fetchVehicles(token, page);
    } catch (reason) {
      setVehicleError(reason instanceof Error ? reason.message : "Unable to save vehicle");
    }
  }

  function startEdit(vehicle: VehicleDetail) {
    setEditingVehicleId(vehicle.id);
    setVehicleForm({
      base_model_name: vehicle.base_model_name,
      rlf_id: vehicle.rlf_id ?? "",
      rm_id: vehicle.rm_id ?? "",
      rm_rlf_band: vehicle.rm_rlf_band ?? "",
      ip_id: vehicle.ip_id ?? "",
      ip_band: vehicle.ip_band ?? "",
      evap_id: vehicle.evap_id ?? "",
      pr_id: vehicle.pr_id ?? "",
      df_id: vehicle.df_id ?? "",
      ob_id: vehicle.ob_id ?? "",
      er_id: vehicle.er_id ?? "",
      pems_id: vehicle.pems_id ?? "",
      variants: vehicle.variants.map((variant) => ({
        variant_name: variant.variant_name,
        equation: variant.equation ?? "",
        cycle_energy_demand: variant.cycle_energy_demand ?? "",
        co2: variant.co2 ?? "",
      })),
    });
    setSelected(null);
    setView("add");
  }

  async function deleteVehicle(id: number) {
    if (!token || !window.confirm("Are you sure you want to delete this vehicle?")) return;
    try {
      await api(`/vehicles/${id}`, { method: "DELETE" }, token);
      const nextPage = results && results.items.length === 1 && page > 1 ? page - 1 : page;
      setPage(nextPage);
      await fetchVehicles(token, nextPage);
    } catch (reason) {
      setSearchError(reason instanceof Error ? reason.message : "Unable to delete vehicle");
    }
  }

  async function uploadWorkbook() {
    if (!token || !file) return;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("mode", importMode);
    setUploadState({ status: "Uploading...", summary: "Uploading workbook" });
    try {
      const response = await fetch(`${API_BASE}/imports/vehicles`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const rawPayload = await response.json() as { detail?: unknown } & Partial<ImportResult>;
      const payload = rawPayload as ImportResult;
      if (!response.ok) throw new Error(rawPayload.detail ? String(rawPayload.detail) : "Upload failed");
      const summary = `Created ${payload.created_vehicles} vehicles • Updated ${payload.updated_vehicles} • Variants ${payload.created_variants}`;
      setUploadState({ status: "Import completed", summary });
      setFile(null);
      setImportPreview(null);
      await fetchVehicles(token);
    } catch (reason) {
      setUploadState({ status: "Import failed", summary: reason instanceof Error ? reason.message : "Upload failed" });
    }
  }

  async function previewWorkbook() {
    if (!token || !file) return;
    const formData = new FormData();
    formData.append("file", file);
    setUploadState({ status: labels.common.loading, summary: labels.common.preview });
    try {
      const response = await fetch(`${API_BASE}/imports/vehicles/preview`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const payload = await response.json() as ImportPreview;
      if (!response.ok) throw new Error(String(payload));
      setImportPreview(payload);
      setUploadState({ status: labels.common.preview, summary: payload.can_import ? `${payload.total_rows} rows ready` : "Validation errors must be fixed before import" });
    } catch (reason) {
      setUploadState({ status: "Preview failed", summary: reason instanceof Error ? reason.message : "Preview failed" });
    }
  }

  async function loadUsers() {
    if (!token || !admin) return;
    try {
      const payload = await api<{ items: AuthUser[] }>("/users", { method: "GET" }, token);
      setUsers(payload.items);
    } catch {
      setUsers([]);
    }
  }

  async function setUserAccess(entry: AuthUser, allowAccess: boolean) {
    if (!token) return;
    try {
      const updated = await api<AuthUser>(`/users/${entry.id}/access`, {
        method: "PATCH",
        body: JSON.stringify({ allow_access: allowAccess }),
      }, token);
      setUsers((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (reason) {
      setSearchError(reason instanceof Error ? reason.message : "Unable to update access");
    }
  }

  async function createUser(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setUserError("");
    try {
      const created = await api<AuthUser>("/users", { method: "POST", body: JSON.stringify({ ...userForm, allow_access: false }) }, token);
      setUsers((current) => [...current, created].sort((left, right) => left.username.localeCompare(right.username)));
      setUserForm({ username: "", email: "", role: "USER" });
    } catch (reason) {
      setUserError(reason instanceof Error ? reason.message : "Unable to create user");
    }
  }

  async function deleteUser(userId: number) {
    if (!token || !window.confirm("Are you sure you want to delete this user?")) return;
    try {
      await api(`/users/${userId}`, { method: "DELETE" }, token);
      setUsers((current) => current.filter((entry) => entry.id !== userId));
    } catch (reason) {
      setUserError(reason instanceof Error ? reason.message : "Unable to delete user");
    }
  }

  async function changePassword(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setPasswordState("");
    try {
      await api("/auth/change-password", { method: "POST", body: JSON.stringify(passwordForm) }, token);
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
      setPasswordState("Password changed successfully. Please sign in again.");
    } catch (reason) {
      setPasswordState(reason instanceof Error ? reason.message : "Unable to change password");
    }
  }

  useEffect(() => {
    if (token && admin && view === "users") {
      void loadUsers();
    }
  }, [token, admin, view]);

  if (!token || !user) {
    return (
      <main className="login-shell">
        <section className="login-panel">
          <p className="brand">VEHICLE TRACKER</p>
          <h1>{authMode === "login" ? "Vehicle Master Management" : authMode === "register" ? "Create account" : authMode === "forgot" ? "Recover access" : authMode === "verify-registration" ? "Verify registration" : "Reset password"}</h1>

          {authMode === "login" && (
            <form className="login-form" onSubmit={handleLogin}>
              <label>
                <span>{labels.user.username}</span>
                <input type="text" value={loginForm.username} onChange={(event) => setLoginForm((current) => ({ ...current, username: event.target.value }))} />
              </label>
              <label>
                <span>{labels.user.password}</span>
                <input type="password" value={loginForm.password} onChange={(event) => setLoginForm((current) => ({ ...current, password: event.target.value }))} />
              </label>
              {loginError && <div className="error-box">{loginError}</div>}
              <button type="submit" className="primary-button">{labels.auth.signIn}</button>
              <div className="auth-actions-row">
                <button type="button" className="ghost-button" onClick={() => { setAuthMode("register"); setLoginError(""); }}>
                  {labels.auth.register}
                </button>
                <button type="button" className="ghost-button" onClick={() => { setAuthMode("forgot"); setLoginError(""); }}>
                  {labels.auth.forgotPassword}
                </button>
              </div>
            </form>
          )}

          {authMode === "register" && (
            <form className="login-form" onSubmit={handleRegistration}>
              <label>
                <span>{labels.user.username}</span>
                <input type="text" value={registrationForm.username} onChange={(event) => setRegistrationForm((current) => ({ ...current, username: event.target.value }))} />
              </label>
              <label>
                <span>{labels.user.email}</span>
                <input type="email" value={registrationForm.email} onChange={(event) => setRegistrationForm((current) => ({ ...current, email: event.target.value }))} />
              </label>
              <label>
                <span>{labels.user.password}</span>
                <input type="password" value={registrationForm.password} onChange={(event) => setRegistrationForm((current) => ({ ...current, password: event.target.value }))} />
              </label>
              {loginError && <div className="error-box">{loginError}</div>}
              <button type="submit" className="primary-button">{labels.auth.register}</button>
              <button type="button" className="ghost-button" onClick={() => { setAuthMode("login"); setLoginError(""); }}>
                {labels.auth.signIn}
              </button>
            </form>
          )}

          {authMode === "verify-registration" && pendingRegistration && (
            <form className="login-form" onSubmit={handleVerifyRegistration}>
              <label>
                <span>{labels.user.username}</span>
                <input type="text" value={pendingRegistration.username} readOnly />
              </label>
              <label>
                <span>{labels.user.email}</span>
                <input type="email" value={pendingRegistration.email} readOnly />
              </label>
              <label>
                <span>{labels.auth.otpCode}</span>
                <input type="text" inputMode="numeric" autoComplete="one-time-code" value={registrationOtp} maxLength={6} onChange={(event) => setRegistrationOtp(event.target.value.replace(/\D/g, "").slice(0, 6))} />
              </label>
              {loginError && <div className="error-box">{loginError}</div>}
              <button type="submit" className="primary-button">Verify OTP</button>
              <button type="button" className="ghost-button" disabled={resendSeconds > 0} onClick={() => void resendRegistrationOtp()}>
                {resendSeconds > 0 ? `Resend in ${Math.floor(resendSeconds / 60)}:${String(resendSeconds % 60).padStart(2, "0")}` : "Resend code"}
              </button>
              <button type="button" className="ghost-button" onClick={() => { setPendingRegistration(null); setAuthMode("register"); setLoginError(""); }}>
                Back
              </button>
            </form>
          )}

          {authMode === "forgot" && (
            <form className="login-form" onSubmit={handleForgotPassword}>
              <label>
                <span>{labels.user.email}</span>
                <input type="email" value={forgotPasswordEmail} onChange={(event) => setForgotPasswordEmail(event.target.value)} />
              </label>
              {loginError && <div className="error-box">{loginError}</div>}
              <button type="submit" className="primary-button">{labels.auth.forgotPassword}</button>
              <button type="button" className="ghost-button" onClick={() => { setAuthMode("login"); setLoginError(""); setForgotPasswordEmail(""); }}>
                {labels.auth.signIn}
              </button>
            </form>
          )}

          {authMode === "verify-reset" && (
            <form className="login-form" onSubmit={handleVerifyReset}>
              <label>
                <span>{labels.user.email}</span>
                <input type="email" value={forgotPasswordEmail} readOnly />
              </label>
              <label>
                <span>{labels.auth.otpCode}</span>
                <input type="text" inputMode="numeric" autoComplete="one-time-code" value={resetForm.otp} maxLength={6} onChange={(event) => setResetForm((current) => ({ ...current, otp: event.target.value.replace(/\D/g, "").slice(0, 6) }))} />
              </label>
              {loginError && <div className="error-box">{loginError}</div>}
              <button type="submit" className="primary-button">Verify OTP</button>
              <button type="button" className="ghost-button" disabled={resendSeconds > 0} onClick={() => void resendPasswordResetOtp()}>
                {resendSeconds > 0 ? `Resend in ${Math.floor(resendSeconds / 60)}:${String(resendSeconds % 60).padStart(2, "0")}` : "Resend code"}
              </button>
              <button type="button" className="ghost-button" onClick={() => { setAuthMode("forgot"); setLoginError(""); }}>
                Back
              </button>
            </form>
          )}

          {resetToken && authMode === "set-reset-password" && (
            <form className="login-form" onSubmit={handleResetPassword}>
              <label>
                <span>{labels.auth.newPassword}</span>
                <input type="password" value={resetForm.new_password} onChange={(event) => setResetForm((current) => ({ ...current, new_password: event.target.value }))} />
              </label>
              <label>
                <span>{labels.auth.confirmPassword}</span>
                <input type="password" value={resetForm.confirm_password} onChange={(event) => setResetForm((current) => ({ ...current, confirm_password: event.target.value }))} />
              </label>
              {loginError && <div className="error-box">{loginError}</div>}
              <button type="submit" className="primary-button">{labels.auth.resetPassword}</button>
            </form>
          )}
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">VehicleTracker</div>
        <nav className="nav">
          {navItems.map((item) => {
            const icon = item.value === "search" ? <Search size={17} />
              : item.value === "add" ? <CarFront size={17} />
                : item.value === "upload" ? <Upload size={17} />
                  : item.value === "users" ? <Users size={17} />
                    : item.value === "profile" ? <UserRound size={17} />
                      : <LogOut size={17} />;
            if (item.value === "logout") {
              return (
                <button key={item.value} className="nav-item danger" onClick={handleLogout}>
                  <span className="nav-icon">{icon}</span>{item.label}
                </button>
              );
            }
            return (
              <button
                key={item.value}
                className={view === item.value ? "nav-item active" : "nav-item"}
                onClick={() => {
                  if (item.value === "logout") return;
                  setView(item.value);
                }}
              >
                <span className="nav-icon">{icon}</span>{item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <section className="content">
        {view === "search" && (
          <>
            <header className="toolbar">
              <div>
                <p className="eyebrow">Vehicle Search</p>
                <h2>Search vehicles</h2>
              </div>
              <button className="ghost-button" onClick={() => setSelected(null)}>{profile?.username ?? user.username}</button>
            </header>
            <div className="filter-card">
              <div className="card-header">
                <h3>Vehicle Filters</h3>
                <div className="inline-actions">
                  <button className="ghost-button small" onClick={() => { void resetFilters(); }}><RotateCcw size={14} /> {labels.common.reset}</button>
                  <button className="primary-button compact" onClick={() => { setPage(1); void fetchVehicles(token, 1); }}>
                    <Search size={14} />
                    {labels.common.apply}
                  </button>
                  <button className="primary-button compact" onClick={() => { void exportVehicles(); }}><Download size={14} /> {labels.common.export}</button>
                </div>
              </div>
              <div className="filter-grid">
                {FILTER_FIELDS.map((field) => (
                  <label key={field.key} className="field-box">
                    <span>{field.label}</span>
                    <input
                      value={filters[field.key] ?? ""}
                      onChange={(event) => updateFilter(field.key, event.target.value)}
                    />
                  </label>
                ))}
              </div>
            </div>

            <div className="results-wrap">
              {searchError && <div className="error-box">{searchError}</div>}
              {loading && <div className="loading">Loading vehicles...</div>}
              {!loading && results && results.items.length === 0 && <div className="empty-state">No vehicles found. Try changing your filter criteria.</div>}
              {results?.items.map((vehicle) => (
                <div key={vehicle.id} className="vehicle-card">
                  <div className="vehicle-card-row">
                    <button className="vehicle-card-main" onClick={() => void openVehicle(vehicle.id)}>
                      <strong>{vehicle.base_model_name}</strong>
                      <span>{vehicle.ip_id ?? "--"} • {vehicle.rlf_id ?? "--"}</span>
                      <small>{vehicle.variant_count} {labels.vehicle.variants}</small>
                    </button>
                    {admin && (
                      <div className="action-stack">
                        <button className="ghost-button small" onClick={() => void openVehicle(vehicle.id)}>{labels.common.edit}</button>
                        <button className="danger-button small" onClick={() => void deleteVehicle(vehicle.id)}>{labels.common.delete}</button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {results && results.total_pages > 0 && <div className="pagination"><button disabled={page <= 1} onClick={() => { const next = page - 1; setPage(next); void fetchVehicles(token, next); }}>{labels.common.previous}</button><span>{page} / {results.total_pages}</span><button disabled={page >= results.total_pages} onClick={() => { const next = page + 1; setPage(next); void fetchVehicles(token, next); }}>{labels.common.next}</button></div>}
            </div>
          </>
        )}

        {view === "add" && (
          <div className="panel">
            <div className="card-header">
              <h2>{editingVehicleId ? labels.vehicle.editTitle : labels.vehicle.createTitle}</h2>
            </div>
            <form className="vehicle-form" onSubmit={saveVehicle}>
              <div className="input-row two-col">
                <label>
                  <span>{labels.vehicle.baseModelName}</span>
                  <input value={vehicleForm.base_model_name} onChange={(event) => setVehicleForm((current) => ({ ...current, base_model_name: event.target.value }))} />
                </label>
              </div>
              <div className="input-row two-col">
                {[
                  ["rlf_id", "RLF ID"],
                  ["rm_id", "RM ID"],
                  ["rm_rlf_band", "RM/RLF Band"],
                  ["ip_id", "IP ID"],
                  ["ip_band", "IP Band"],
                  ["evap_id", "EVAP ID"],
                  ["pr_id", "PR ID"],
                  ["df_id", "DF ID"],
                  ["ob_id", "OB ID"],
                  ["er_id", "ER ID"],
                  ["pems_id", "PEMS ID"],
                ].map(([key, label]) => (
                  <label key={key}>
                    <span>{label}</span>
                    <input value={vehicleForm[key as keyof typeof vehicleForm] as string} onChange={(event) => setVehicleForm((current) => ({ ...current, [key]: event.target.value }))} />
                  </label>
                ))}
              </div>
              <div className="variants-box">
                <div className="card-header small-space">
                  <h3>Variants</h3>
                  <button type="button" className="primary-button compact" onClick={() => openNewVariant("vehicle")}><Plus size={15} /> Add Variant</button>
                </div>
                {vehicleForm.variants.length === 0 ? <div className="empty-state small">No variants added.</div> : vehicleForm.variants.map((variant, index) => (
                  <div key={`variant-${index}`} className="variant-inline">
                    <div className="variant-summary">
                      <strong>{variant.variant_name}</strong>
                      <span>{variant.equation || "No equation"} · Cycle: {variant.cycle_energy_demand || "--"} · CO2: {variant.co2 || "--"}</span>
                    </div>
                    <div className="variant-inline-actions">
                      <button type="button" className="ghost-button small" aria-label="Edit variant" onClick={() => editVehicleVariant(index)}><Pencil size={14} /></button>
                      <button type="button" className="danger-button small" aria-label="Delete variant" onClick={() => removeVehicleVariant(index)}><Trash2 size={14} /></button>
                    </div>
                  </div>
                ))}
              </div>
              {vehicleError && <div className="error-box">{vehicleError}</div>}
              <div className="actions-row">
                <button type="submit" className="primary-button">{labels.vehicle.save}</button>
                <button type="button" className="ghost-button" onClick={() => { setVehicleForm(EMPTY_VEHICLE_FORM); setEditingVehicleId(null); }}>{labels.common.cancel}</button>
              </div>
            </form>
          </div>
        )}

        {view === "upload" && (
          <div className="panel">
            <h2>Vehicle Upload</h2>
            <div className="upload-box">
              <p>Upload Vehicle Excel</p>
              <label className="upload-zone">
                <input type="file" accept=".xlsx" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
                <span>{file ? file.name : "Choose File"}</span>
              </label>
              {file && <div className="file-meta">Selected file: {file.name} • {Math.round(file.size / 1024)} KB</div>}
              {uploadState && <div className="status-box"><strong>{uploadState.status}</strong><span>{uploadState.summary}</span></div>}
              {importPreview && <div className="status-box"><strong>{importPreview.can_import ? "Workbook ready" : "Workbook has validation errors"}</strong><span>{importPreview.base_models_detected} vehicles • {importPreview.variants_detected} variants • {importPreview.warnings.length} warnings</span></div>}
              <div className="actions-row">
                <button className="ghost-button" onClick={() => void previewWorkbook()}>{labels.common.preview}</button>
                <select value={importMode} onChange={(event) => setImportMode(event.target.value as "upsert" | "replace")} aria-label="Import mode">
                  <option value="upsert">Upsert</option>
                  <option value="replace">Replace variants</option>
                </select>
                <button className="primary-button" disabled={!importPreview?.can_import} onClick={() => void uploadWorkbook()}>{labels.common.upload}</button>
              </div>
            </div>
          </div>
        )}

        {view === "profile" && (
          <div className="panel">
            <h2>Profile</h2>
            <div className="profile-card">
              <div><span>Username</span><strong>{profile?.username ?? user.username}</strong></div>
              <div><span>Email</span><strong>{profile?.email ?? user.email}</strong></div>
              <div><span>Role</span><strong>{profile?.role ?? user.role}</strong></div>
              <div><span>Account status</span><strong>{profile?.is_active ?? user.is_active ? "Active" : "Inactive"}</strong></div>
              <div><span>Access status</span><strong>{profile?.allow_access ?? user.allow_access ? "Allowed" : "Blocked"}</strong></div>
            </div>
            <form className="vehicle-form" onSubmit={changePassword}>
              <h3>{labels.auth.newPassword}</h3>
              <label><span>{labels.auth.currentPassword}</span><input type="password" value={passwordForm.current_password} onChange={(event) => setPasswordForm((current) => ({ ...current, current_password: event.target.value }))} /></label>
              <label><span>{labels.auth.newPassword}</span><input type="password" value={passwordForm.new_password} onChange={(event) => setPasswordForm((current) => ({ ...current, new_password: event.target.value }))} /></label>
              <label><span>{labels.auth.confirmPassword}</span><input type="password" value={passwordForm.confirm_password} onChange={(event) => setPasswordForm((current) => ({ ...current, confirm_password: event.target.value }))} /></label>
              {passwordState && <div className="status-box">{passwordState}</div>}
              <button type="submit" className="primary-button">{labels.common.save}</button>
            </form>
          </div>
        )}

        {view === "users" && (
          <div className="panel">
            <div className="card-header">
              <h2>User Management</h2>
            </div>
            <form className="user-create-form" onSubmit={createUser}>
              <label><span>{labels.user.username}</span><input value={userForm.username} onChange={(event) => setUserForm((current) => ({ ...current, username: event.target.value }))} /></label>
              <label><span>{labels.user.email}</span><input type="email" value={userForm.email} onChange={(event) => setUserForm((current) => ({ ...current, email: event.target.value }))} /></label>
              <label><span>{labels.user.role}</span><select value={userForm.role} onChange={(event) => setUserForm((current) => ({ ...current, role: event.target.value }))}><option value="USER">USER</option><option value="ADMIN">ADMIN</option></select></label>
              <button type="submit" className="primary-button">{labels.user.create}</button>
            </form>
            <p className="file-meta">{labels.user.initialPassword}</p>
            {userError && <div className="error-box">{userError}</div>}
            <div className="user-table-wrap">
              <table className="user-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Access</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 ? (
                    <tr><td colSpan={6}>{labels.common.noResults}</td></tr>
                  ) : users.map((entry) => (
                    <tr key={entry.id}>
                      <td>{entry.username}</td>
                      <td>{entry.email}</td>
                      <td>{entry.role}</td>
                      <td>{entry.allow_access ? "Allowed" : "Blocked"}</td>
                      <td>{entry.is_active ? "Active" : "Inactive"}</td>
                      <td className="user-actions">
                        <button className="ghost-button small" onClick={() => void setUserAccess(entry, !entry.allow_access)}>{entry.allow_access ? labels.user.revoke : labels.user.grant}</button>
                        <button className="danger-button small" onClick={() => void deleteUser(entry.id)}>{labels.common.delete}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <div className="modal-card" onClick={(event) => event.stopPropagation()}>
            <button className="close-button" onClick={() => setSelected(null)} aria-label={labels.common.close}>×</button>
            <h3>{selected.base_model_name}</h3>
            {admin && <div className="actions-row"><button className="ghost-button" onClick={() => startEdit(selected)}>{labels.common.edit}</button><button className="danger-button" onClick={() => { void deleteVehicle(selected.id); setSelected(null); }}>{labels.common.delete}</button></div>}
            <div className="modal-grid">
              {[
                ["rlf_id", "RLF ID"],
                ["rm_id", "RM ID"],
                ["ip_id", "IP ID"],
                ["evap_id", "EVAP ID"],
                ["pr_id", "PR ID"],
                ["df_id", "DF ID"],
                ["ob_id", "OB ID"],
                ["er_id", "ER ID"],
                ["pems_id", "PEMS ID"],
              ].map(([key, label]) => (
                <div key={key}>
                  <span>{label}</span>
                  <strong>{String(selected[key as keyof Omit<VehicleDetail, "variants">] ?? "--")}</strong>
                </div>
              ))}
            </div>
            <div className="variant-grid">
              <div className="card-header variant-header">
                <h4>{labels.vehicle.variants}</h4>
                {admin && <button type="button" className="primary-button compact" onClick={() => openNewVariant("detail")}><Plus size={14} /> Add Variant</button>}
              </div>
              <div className="variant-scroll" onScroll={(event) => {
                const element = event.currentTarget;
                if (element.scrollTop + element.clientHeight >= element.scrollHeight - 16 && variantPage < variantTotalPages && !variantLoading) {
                  void loadVariants(selected.id, variantPage + 1, true);
                }
              }}>
                {variantItems.length === 0 && !variantLoading ? <div className="empty-state small">{labels.vehicle.noVariants}</div> : variantItems.map((variant) => (
                  <div key={variant.id} className="variant-tile">
                    <div className="variant-tile-main">
                      <strong>{variant.variant_name}</strong>
                      <small>Equation: {variant.equation || "--"}</small>
                      <small>Cycle energy demand: {variant.cycle_energy_demand || "--"}</small>
                      <small>CO2: {variant.co2 || "--"}</small>
                    </div>
                    {admin && <div className="variant-inline-actions">
                      <button className="ghost-button small" aria-label="Edit variant" onClick={() => editDetailVariant(variant)}><Pencil size={14} /></button>
                      <button className="danger-button small" aria-label="Delete variant" onClick={() => void removeDetailVariant(variant.id)}><Trash2 size={14} /></button>
                    </div>}
                  </div>
                ))}
                {variantLoading && <div className="loading">{labels.vehicle.loadingVariants}</div>}
              </div>
            </div>
          </div>
        </div>
      )}

      {variantModalOpen && (
        <div className="modal-backdrop" onClick={() => setVariantModalOpen(false)}>
          <form className="modal-card variant-editor" onSubmit={(event) => { event.preventDefault(); void saveVariantDraft(); }} onClick={(event) => event.stopPropagation()}>
            <button type="button" className="close-button" onClick={() => setVariantModalOpen(false)} aria-label={labels.common.close}>×</button>
            <h3>{variantEditIndex === null && variantEditId === null ? "Add variant" : "Edit variant"}</h3>
            <div className="variant-form-grid">
              <label><span>Variant Name</span><input autoFocus required maxLength={512} value={variantDraft.variant_name} onChange={(event) => setVariantDraft((current) => ({ ...current, variant_name: event.target.value }))} /></label>
              <label><span>Equation</span><input maxLength={1024} value={variantDraft.equation} onChange={(event) => setVariantDraft((current) => ({ ...current, equation: event.target.value }))} /></label>
              <label><span>Cycle Energy Demand</span><input maxLength={255} value={variantDraft.cycle_energy_demand} onChange={(event) => setVariantDraft((current) => ({ ...current, cycle_energy_demand: event.target.value }))} /></label>
              <label><span>CO2</span><input maxLength={255} value={variantDraft.co2} onChange={(event) => setVariantDraft((current) => ({ ...current, co2: event.target.value }))} /></label>
            </div>
            <div className="actions-row"><button type="submit" className="primary-button">Save Variant</button><button type="button" className="ghost-button" onClick={() => setVariantModalOpen(false)}>Cancel</button></div>
          </form>
        </div>
      )}
    </main>
  );
}