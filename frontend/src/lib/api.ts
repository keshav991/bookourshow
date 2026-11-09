import { supabase } from './supabaseClient';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export interface UserProfile {
  id: string;
  email: string | null;
  full_name: string | null;
  role: string;
}

export interface BookingsDemoResponse {
  user_id: string;
  email: string | null;
  message: string;
  bookings: any[];
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Reusable fetch wrapper that automatically attaches the active Supabase JWT Bearer token
 * to every request directed to FastAPI.
 */
async function fetchWithAuth<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // Retrieve current session from Supabase
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    let errorMessage = 'Request failed';
    if (isJson && data?.detail) {
      errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } else if (response.status === 401) {
      errorMessage = 'Session expired or unauthorized. Please log in again.';
    } else if (response.status === 403) {
      errorMessage = 'Access denied: insufficient permissions.';
    } else if (response.status === 404) {
      errorMessage = 'Resource not found.';
    }

    throw new ApiError(response.status, errorMessage, data);
  }

  return data as T;
}

export const api = {
  /**
   * Fetch current user profile from FastAPI PostgreSQL public.profiles
   */
  async getUserProfile(): Promise<UserProfile> {
    return fetchWithAuth<UserProfile>('/users/me', {
      method: 'GET',
    });
  },

  /**
   * Update full name on current user profile in PostgreSQL
   */
  async updateUserProfile(fullName: string): Promise<UserProfile> {
    return fetchWithAuth<UserProfile>('/users/me', {
      method: 'PUT',
      body: JSON.stringify({ full_name: fullName }),
    });
  },

  /**
   * Call booking ownership demo to verify strict user data isolation
   */
  async getUserBookingsDemo(): Promise<BookingsDemoResponse> {
    return fetchWithAuth<BookingsDemoResponse>('/users/me/bookings-demo', {
      method: 'GET',
    });
  },

  /**
   * Revoke session on backend Supabase instance
   */
  async backendLogout(): Promise<{ message: string }> {
    return fetchWithAuth<{ message: string }>('/auth/logout', {
      method: 'POST',
    });
  },

  /**
   * System health check
   */
  async checkHealth(): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE_URL}/health`);
    return res.json();
  },
};
