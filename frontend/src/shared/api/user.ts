import {
  type ProfileConfigResponse,
  type UserProfile,
  type UserProfileUpdate,
} from "../types/api";
import { aiGet, aiPost, aiPut, aiUpload } from "./core";

export async function fetchProfileConfig(): Promise<ProfileConfigResponse> {
  return aiGet<ProfileConfigResponse>("/users/profile/config");
}

export async function fetchUserProfile(userId: string): Promise<UserProfile> {
  return aiGet<UserProfile>(`/users/${userId}`);
}

export async function updateUserProfile(
  userId: string,
  data: UserProfileUpdate,
): Promise<UserProfile> {
  return aiPut<UserProfile>(`/users/${userId}`, data);
}

export async function uploadProfilePic(
  userId: string,
  file: File,
): Promise<{ profile_pic_url: string }> {
  const formData = new FormData();
  formData.append("file", file);
  return aiUpload<{ profile_pic_url: string }>(
    `/users/${userId}/profile-pic`,
    formData,
  );
}

export async function submitKyc(
  userId: string,
  panCardNumber: string,
  aadhaarNumber?: string,
): Promise<{ kyc_status: string; kyc_submitted_at: string; message: string }> {
  return aiPost(`/users/${userId}/kyc/submit`, {
    pan_card_number: panCardNumber,
    aadhaar_number: aadhaarNumber,
  });
}

export async function fetchKycStatus(
  userId: string,
): Promise<{ kyc_status: string; kyc_submitted_at: string | null; pan_card_number: string | null }> {
  return aiGet(`/users/${userId}/kyc/status`);
}

export async function verifyKyc(
  userId: string,
): Promise<{ kyc_status: string; message: string }> {
  return aiPost(`/users/${userId}/kyc/verify`, {});
}
