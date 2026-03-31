import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  AtSign,
  Calendar,
  Camera,
  Check,
  CircleCheck,
  CircleUserRound,
  Clock3,
  CreditCard,
  Database,
  Fingerprint,
  GraduationCap,
  Loader2,
  Mail,
  MapPin,
  Moon,
  Phone,
  Settings,
  ShieldAlert,
  Sun,
  TrendingUp,
  Upload,
  User,
} from "lucide-react";

import {
  fetchProfileConfig,
  fetchUserProfile,
  type ProfileOption,
  submitKyc,
  updateUserProfile,
  uploadProfilePic,
  verifyKyc,
} from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";

interface ProfileViewProps {
  dataMode: "live" | "demo";
  theme: "light" | "dark";
  onToggleTheme: () => void;
  onToggleDataMode: () => void;
  pushToast: (message: string, tone?: "info" | "success" | "warning") => void;
}

interface ProfileState {
  full_name: string;
  username: string;
  email: string;
  phone_number: string;
  date_of_birth: string;
  address: string;
  pan_card_number: string;
  aadhaar_number: string;
  expertise_level: string;
  risk_tolerance: string;
  investment_horizon: string;
  profile_pic_url: string;
  kyc_status: string;
}

interface ProfileConfigState {
  expertise_levels: ProfileOption[];
  risk_tolerance_levels: ProfileOption[];
  investment_horizons: ProfileOption[];
  defaults: Record<string, string>;
}

const DEFAULT_PROFILE_CONFIG: ProfileConfigState = {
  expertise_levels: [
    { value: "beginner", label: "Beginner" },
    { value: "intermediate", label: "Intermediate" },
    { value: "advanced", label: "Advanced" },
  ],
  risk_tolerance_levels: [
    { value: "conservative", label: "Conservative" },
    { value: "moderate", label: "Moderate" },
    { value: "aggressive", label: "Aggressive" },
  ],
  investment_horizons: [
    { value: "short", label: "Short Term (0-1 yr)" },
    { value: "medium", label: "Medium Term (1-5 yr)" },
    { value: "long", label: "Long Term (5+ yr)" },
  ],
  defaults: {
    expertise_level: "beginner",
    risk_tolerance: "moderate",
    investment_horizon: "medium",
  },
};

export function ProfileView(props: ProfileViewProps) {
  const [profileConfig, setProfileConfig] = useState<ProfileConfigState>(DEFAULT_PROFILE_CONFIG);
  const [profile, setProfile] = useState<ProfileState>({
    full_name: "",
    username: "",
    email: "",
    phone_number: "",
    date_of_birth: "",
    address: "",
    pan_card_number: "",
    aadhaar_number: "",
    expertise_level: "beginner",
    risk_tolerance: "moderate",
    investment_horizon: "medium",
    profile_pic_url: "",
    kyc_status: "not_started",
  });
  const [saving, setSaving] = useState(false);
  const [kycSubmitting, setKycSubmitting] = useState(false);
  const [kycStep, setKycStep] = useState(0);
  const avatarInputRef = useRef<HTMLInputElement | null>(null);

  const userId = useMemo(() => {
    let id = localStorage.getItem("equityai-user-id");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("equityai-user-id", id);
    }
    return id;
  }, []);

  useEffect(() => {
    if (props.dataMode !== "live") return;
    (async () => {
      try {
        const config = await fetchProfileConfig();
        setProfileConfig({
          expertise_levels: config.expertise_levels,
          risk_tolerance_levels: config.risk_tolerance_levels,
          investment_horizons: config.investment_horizons,
          defaults: config.defaults,
        });
      } catch {
        // Keep static fallback config if endpoint is unavailable.
      }
    })();
  }, [props.dataMode]);

  useEffect(() => {
    if (props.dataMode !== "live") return;
    (async () => {
      try {
        const p = await fetchUserProfile(userId);
        setProfile({
          full_name: p.full_name || "",
          username: p.username || "",
          email: p.email || "",
          phone_number: p.phone_number || "",
          date_of_birth: p.date_of_birth || "",
          address: p.address || "",
          pan_card_number: p.pan_card_number || "",
          aadhaar_number: p.aadhaar_number || "",
          expertise_level: p.expertise_level || "beginner",
          risk_tolerance: p.risk_tolerance || "moderate",
          investment_horizon: p.investment_horizon || "medium",
          profile_pic_url: p.profile_pic_url || "",
          kyc_status: p.kyc_status || "not_started",
        });
        if (p.kyc_status === "verified") setKycStep(4);
        else if (p.kyc_status === "pending") setKycStep(2);
        else setKycStep(0);
      } catch {
        // profile may not exist yet
      }
    })();
  }, [props.dataMode, userId]);

  const handleField = useCallback((field: keyof ProfileState, value: string) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      if (props.dataMode === "live") {
        await updateUserProfile(userId, {
          full_name: profile.full_name || undefined,
          username: profile.username || undefined,
          email: profile.email || undefined,
          phone_number: profile.phone_number || undefined,
          date_of_birth: profile.date_of_birth || undefined,
          address: profile.address || undefined,
          expertise_level: profile.expertise_level,
          risk_tolerance: profile.risk_tolerance,
          investment_horizon: profile.investment_horizon,
        });
      }
      props.pushToast("Profile saved successfully", "success");
    } catch {
      props.pushToast("Failed to save profile", "warning");
    } finally {
      setSaving(false);
    }
  }, [profile, props, userId]);

  const handleAvatarUpload = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      try {
        if (props.dataMode === "live") {
          const result = await uploadProfilePic(userId, file);
          setProfile((prev) => ({ ...prev, profile_pic_url: result.profile_pic_url }));
        } else {
          setProfile((prev) => ({ ...prev, profile_pic_url: URL.createObjectURL(file) }));
        }
        props.pushToast("Profile picture updated", "success");
      } catch {
        props.pushToast("Failed to upload picture", "warning");
      }
      if (event.target) event.target.value = "";
    },
    [props, userId]
  );

  const handleKycSubmit = useCallback(async () => {
    if (
      !profile.pan_card_number ||
      !/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(profile.pan_card_number.toUpperCase())
    ) {
      props.pushToast("Please enter a valid PAN (e.g. ABCDE1234F)", "warning");
      return;
    }
    setKycSubmitting(true);
    setKycStep(1);

    try {
      if (props.dataMode === "live") {
        await submitKyc(userId, profile.pan_card_number.toUpperCase(), profile.aadhaar_number || undefined);
        setKycStep(2);
        setProfile((prev) => ({ ...prev, kyc_status: "pending" }));

        await new Promise((r) => setTimeout(r, 1500));
        setKycStep(3);

        await new Promise((r) => setTimeout(r, 1000));
        await verifyKyc(userId);
        setKycStep(4);
        setProfile((prev) => ({ ...prev, kyc_status: "verified" }));
        props.pushToast("KYC verified successfully!", "success");
      } else {
        await new Promise((r) => setTimeout(r, 800));
        setKycStep(2);
        setProfile((prev) => ({ ...prev, kyc_status: "pending" }));
        await new Promise((r) => setTimeout(r, 1200));
        setKycStep(3);
        await new Promise((r) => setTimeout(r, 800));
        setKycStep(4);
        setProfile((prev) => ({ ...prev, kyc_status: "verified" }));
        props.pushToast("KYC verified successfully!", "success");
      }
    } catch {
      props.pushToast("KYC verification failed", "warning");
      setKycStep(0);
    } finally {
      setKycSubmitting(false);
    }
  }, [profile.aadhaar_number, profile.pan_card_number, props, userId]);

  const kycSteps = ["Details Submitted", "Document Verification", "Identity Confirmed", "KYC Approved"];
  const kycBadge =
    profile.kyc_status === "verified"
      ? "verified"
      : profile.kyc_status === "pending"
        ? "pending"
        : "not-started";

  const avatarUrl = profile.profile_pic_url
    ? profile.profile_pic_url.startsWith("http") || profile.profile_pic_url.startsWith("blob:")
      ? profile.profile_pic_url
      : `${(import.meta.env.VITE_BACKEND_URL as string | undefined) ?? "http://localhost:8001"}${profile.profile_pic_url}`
    : null;

  return (
    <section className="page-wrap">
      <PageHeader
        title="My Profile"
        subtitle="Manage your account, preferences, and KYC verification."
        dataMode={props.dataMode}
      />

      <div className="profile-header">
        <div className="profile-avatar-wrap" onClick={() => avatarInputRef.current?.click()}>
          <input
            type="file"
            ref={avatarInputRef}
            className="sr-only"
            accept=".jpg,.jpeg,.png,.webp"
            onChange={handleAvatarUpload}
          />
          {avatarUrl ? (
            <img src={avatarUrl} alt="Avatar" className="profile-avatar-img" />
          ) : (
            <div className="profile-avatar-placeholder">
              <CircleUserRound size={48} />
            </div>
          )}
          <div className="profile-avatar-overlay">
            <Camera size={18} />
          </div>
        </div>
        <div className="profile-header-info">
          <h2>{profile.full_name || profile.username || "Set up your profile"}</h2>
          <p className="profile-email">{profile.email || userId}</p>
          <div className="profile-badges">
            <span className={`kyc-badge ${kycBadge}`}>
              {profile.kyc_status === "verified" ? (
                <>
                  <CircleCheck size={13} /> KYC Verified
                </>
              ) : profile.kyc_status === "pending" ? (
                <>
                  <Loader2 size={13} className="spin" /> KYC Pending
                </>
              ) : (
                <>
                  <AlertTriangle size={13} /> KYC Not Started
                </>
              )}
            </span>
            <span className="expertise-badge">
              <GraduationCap size={13} /> {profile.expertise_level}
            </span>
          </div>
        </div>
      </div>

      <div className="profile-section">
        <h3>
          <User size={16} /> Personal Information
        </h3>
        <div className="profile-form">
          <label className="form-field">
            <span>
              <User size={14} /> Full Name
            </span>
            <input
              value={profile.full_name}
              onChange={(e) => handleField("full_name", e.target.value)}
              placeholder="Your full name"
            />
          </label>
          <label className="form-field">
            <span>
              <AtSign size={14} /> Username
            </span>
            <input
              value={profile.username}
              onChange={(e) => handleField("username", e.target.value)}
              placeholder="your_username"
            />
          </label>
          <label className="form-field">
            <span>
              <Mail size={14} /> Email
            </span>
            <input
              type="email"
              value={profile.email}
              onChange={(e) => handleField("email", e.target.value)}
              placeholder="you@example.com"
            />
          </label>
          <label className="form-field">
            <span>
              <Phone size={14} /> Phone Number
            </span>
            <input
              value={profile.phone_number}
              onChange={(e) => handleField("phone_number", e.target.value)}
              placeholder="+91 98765 43210"
            />
          </label>
          <label className="form-field">
            <span>
              <Calendar size={14} /> Date of Birth
            </span>
            <input
              type="date"
              value={profile.date_of_birth}
              onChange={(e) => handleField("date_of_birth", e.target.value)}
            />
          </label>
          <label className="form-field full-width">
            <span>
              <MapPin size={14} /> Address
            </span>
            <input
              value={profile.address}
              onChange={(e) => handleField("address", e.target.value)}
              placeholder="Your address"
            />
          </label>
        </div>
      </div>

      <div className="profile-section">
        <h3>
          <TrendingUp size={16} /> Investment Preferences
        </h3>
        <div className="profile-form">
          <label className="form-field">
            <span>
              <GraduationCap size={14} /> Expertise Level
            </span>
            <select
              value={profile.expertise_level}
              onChange={(e) => handleField("expertise_level", e.target.value)}
            >
              {profileConfig.expertise_levels.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>
              <ShieldAlert size={14} /> Risk Tolerance
            </span>
            <select
              value={profile.risk_tolerance}
              onChange={(e) => handleField("risk_tolerance", e.target.value)}
            >
              {profileConfig.risk_tolerance_levels.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>
              <Clock3 size={14} /> Investment Horizon
            </span>
            <select
              value={profile.investment_horizon}
              onChange={(e) => handleField("investment_horizon", e.target.value)}
            >
              {profileConfig.investment_horizons.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="chip-row" style={{ marginTop: "1rem" }}>
          <button type="button" className="primary-btn" onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 size={14} className="spin" /> Saving...
              </>
            ) : (
              <>
                <Check size={14} /> Save Profile
              </>
            )}
          </button>
        </div>
      </div>

      <div className="profile-section">
        <h3>
          <CreditCard size={16} /> KYC Verification
        </h3>
        <div className="profile-form">
          <label className="form-field">
            <span>
              <CreditCard size={14} /> PAN Card Number
            </span>
            <input
              value={profile.pan_card_number}
              onChange={(e) => handleField("pan_card_number", e.target.value.toUpperCase())}
              placeholder="ABCDE1234F"
              maxLength={10}
            />
          </label>
          <label className="form-field">
            <span>
              <Fingerprint size={14} /> Aadhaar Number
            </span>
            <input
              value={profile.aadhaar_number}
              onChange={(e) => handleField("aadhaar_number", e.target.value)}
              placeholder="1234 5678 9012"
              maxLength={12}
            />
          </label>
        </div>

        <div className="kyc-stepper">
          {kycSteps.map((label, idx) => (
            <div
              key={label}
              className={`kyc-step ${idx < kycStep ? "done" : ""} ${
                idx === kycStep && kycSubmitting ? "active" : ""
              }`}
            >
              <div className="kyc-step-circle">
                {idx < kycStep ? <Check size={14} /> : <span>{idx + 1}</span>}
              </div>
              <p>{label}</p>
              {idx < kycSteps.length - 1 && (
                <div className={`kyc-step-line ${idx < kycStep ? "done" : ""}`} />
              )}
            </div>
          ))}
        </div>

        <div className="chip-row" style={{ marginTop: "1rem" }}>
          {profile.kyc_status !== "verified" && (
            <button
              type="button"
              className="primary-btn"
              onClick={handleKycSubmit}
              disabled={kycSubmitting}
            >
              {kycSubmitting ? (
                <>
                  <Loader2 size={14} className="spin" /> Verifying...
                </>
              ) : (
                <>
                  <Upload size={14} /> Submit KYC
                </>
              )}
            </button>
          )}
          {profile.kyc_status === "verified" && (
            <span className="kyc-badge verified" style={{ fontSize: "0.875rem", padding: "0.5rem 1rem" }}>
              <CircleCheck size={16} /> KYC Verified
            </span>
          )}
        </div>
      </div>

      <div className="profile-section">
        <h3>
          <Settings size={16} /> Account Settings
        </h3>
        <div className="chip-row">
          <button type="button" className="secondary-btn" onClick={props.onToggleTheme}>
            {props.theme === "dark" ? (
              <>
                <Sun size={14} /> Light Mode
              </>
            ) : (
              <>
                <Moon size={14} /> Dark Mode
              </>
            )}
          </button>
          <button type="button" className="secondary-btn" onClick={props.onToggleDataMode}>
            {props.dataMode === "demo" ? (
              <>
                <Database size={14} /> Switch to Live
              </>
            ) : (
              <>
                <Database size={14} /> Switch to Demo
              </>
            )}
          </button>
        </div>
      </div>
    </section>
  );
}
