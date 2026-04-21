import { apiClient } from './client';
import type { AlgorithmOption, FrameData, SimulationRequest, SimulationState } from '../types';

export async function fetchAlgorithms(): Promise<AlgorithmOption[]> {
  const { data } = await apiClient.get<AlgorithmOption[]>('/algorithms');
  return data;
}

export async function startSimulation(payload: SimulationRequest): Promise<SimulationState> {
  const { data } = await apiClient.post<SimulationState>('/simulations', payload);
  return data;
}

export async function pauseSimulation(id: string): Promise<SimulationState> {
  const { data } = await apiClient.post<SimulationState>(`/simulations/${id}/pause`);
  return data;
}

export async function resumeSimulation(id: string): Promise<SimulationState> {
  const { data } = await apiClient.post<SimulationState>(`/simulations/${id}/resume`);
  return data;
}

export async function stopSimulation(id: string): Promise<SimulationState> {
  const { data } = await apiClient.post<SimulationState>(`/simulations/${id}/stop`);
  return data;
}

export async function fetchSimulationState(id: string): Promise<SimulationState> {
  const { data } = await apiClient.get<SimulationState>(`/simulations/${id}/state`);
  return data;
}

export async function fetchFrame(id: string, slot: number): Promise<FrameData> {
  const { data } = await apiClient.get<FrameData>(`/simulations/${id}/frames/${slot}`);
  return data;
}
