import { apiClient } from './client';
import type { Scenario } from '../types';

export async function fetchScenarios(): Promise<Scenario[]> {
  const { data } = await apiClient.get<Scenario[]>('/scenarios');
  return data;
}

export async function createScenario(payload: {
  name: string;
  description?: string;
  centerLng?: number;
  centerLat?: number;
}): Promise<Scenario> {
  const { data } = await apiClient.post<Scenario>('/scenarios', payload);
  return data;
}
