import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function register(email: string, password: string) {
  const response = await axios.post(`${API_BASE_URL}/register`, { email, password });
  return response.data;
}

export async function login(email: string, password: string) {
  const response = await axios.post(`${API_BASE_URL}/login`, { email, password });
  return response.data;
} 