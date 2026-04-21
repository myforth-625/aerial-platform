export type NodeType = 'UAV' | 'HAP' | 'GROUND_STATION' | 'TERMINAL';

export interface Scenario {
  id: string;
  name: string;
  description: string;
  centerLng: number;
  centerLat: number;
  createdAt: number;
}

export interface AlgorithmOption {
  id: string;
  name: string;
  description: string;
}

export type SimulationStatus = 'IDLE' | 'RUNNING' | 'PAUSED' | 'STOPPED';

export interface SimulationRequest {
  scenarioId: string;
  algorithmId: string;
  totalSlots: number;
  nodeCount: number;
  areaSize: number;
  speed: number;
  uavCount?: number;
  hapCount?: number;
  groundStationCount?: number;
  terminalCount?: number;
  nodes?: NodeData[];
}

export interface SimulationState {
  id: string;
  scenarioId: string;
  algorithmId: string;
  status: SimulationStatus;
  currentSlot: number;
  totalSlots: number;
  updatedAt: number;
}

export interface NodeData {
  id: string;
  type: NodeType;
  lng: number;
  lat: number;
  height: number;
  name?: string;
}

export interface LinkData {
  id: string;
  sourceId: string;
  targetId: string;
}

export interface FrameData {
  slot: number;
  nodes: NodeData[];
  links: LinkData[];
  metrics: Record<string, number>;
}
