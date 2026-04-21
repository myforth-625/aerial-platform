package com.minisim.service;

import com.minisim.model.FrameData;
import com.minisim.model.Scenario;
import com.minisim.model.SimulationRequest;
import com.minisim.model.SimulationState;
import com.minisim.model.SimulationStatus;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Service;

@Service
public class SimulationService {
    private final AlgorithmRegistry algorithmRegistry;
    private final ScenarioService scenarioService;
    private final StaticPositionGenerator staticPositionGenerator = new StaticPositionGenerator();
    private final Map<String, SimulationSession> sessions = new ConcurrentHashMap<>();

    public SimulationService(AlgorithmRegistry algorithmRegistry, ScenarioService scenarioService) {
        this.algorithmRegistry = algorithmRegistry;
        this.scenarioService = scenarioService;
    }

    public SimulationState startSimulation(SimulationRequest request) {
        SimulationRequest normalized = normalizeRequest(request);
        boolean algorithmConsumesNodes = algorithmRegistry.consumesNodes(normalized.getAlgorithmId());
        FrameGenerator generator = (hasExplicitNodes(normalized) && !algorithmConsumesNodes)
                ? staticPositionGenerator
                : algorithmRegistry.getGenerator(normalized.getAlgorithmId());
        List<FrameData> frames = generator.generateFrames(normalized);

        SimulationState state = new SimulationState();
        state.setId(UUID.randomUUID().toString());
        state.setScenarioId(normalized.getScenarioId());
        state.setAlgorithmId(normalized.getAlgorithmId());
        state.setStatus(SimulationStatus.RUNNING);
        state.setCurrentSlot(0);
        state.setTotalSlots(frames.size());
        state.setUpdatedAt(System.currentTimeMillis());

        SimulationSession session = new SimulationSession(state, normalized, frames);
        sessions.put(state.getId(), session);
        return state;
    }

    public SimulationState pauseSimulation(String id) {
        SimulationSession session = requireSession(id);
        session.getState().setStatus(SimulationStatus.PAUSED);
        session.getState().setUpdatedAt(System.currentTimeMillis());
        return session.getState();
    }

    public SimulationState resumeSimulation(String id) {
        SimulationSession session = requireSession(id);
        session.getState().setStatus(SimulationStatus.RUNNING);
        session.getState().setUpdatedAt(System.currentTimeMillis());
        return session.getState();
    }

    public SimulationState stopSimulation(String id) {
        SimulationSession session = requireSession(id);
        session.getState().setStatus(SimulationStatus.STOPPED);
        session.getState().setUpdatedAt(System.currentTimeMillis());
        return session.getState();
    }

    public SimulationState getState(String id) {
        return requireSession(id).getState();
    }

    public FrameData getFrame(String id, int slot) {
        SimulationSession session = requireSession(id);
        List<FrameData> frames = session.getFrames();
        if (frames.isEmpty()) {
            return new FrameData();
        }
        int safeSlot = Math.max(0, Math.min(slot, frames.size() - 1));
        session.getState().setCurrentSlot(safeSlot);
        session.getState().setUpdatedAt(System.currentTimeMillis());
        return frames.get(safeSlot);
    }

    private SimulationSession requireSession(String id) {
        SimulationSession session = sessions.get(id);
        if (session == null) {
            throw new IllegalArgumentException("Simulation not found: " + id);
        }
        return session;
    }

    private SimulationRequest normalizeRequest(SimulationRequest request) {
        SimulationRequest normalized = new SimulationRequest();
        normalized.setScenarioId(request.getScenarioId());
        normalized.setAlgorithmId(
                request.getAlgorithmId() == null || request.getAlgorithmId().trim().isEmpty()
                        ? "circle-orbit"
                        : request.getAlgorithmId().trim()
        );
        normalized.setTotalSlots(request.getTotalSlots() > 0 ? request.getTotalSlots() : 30);
        normalized.setNodeCount(request.getNodeCount() > 0 ? request.getNodeCount() : 12);
        normalized.setAreaSize(request.getAreaSize() > 0 ? request.getAreaSize() : 400.0);
        normalized.setSpeed(request.getSpeed() > 0 ? request.getSpeed() : 1.0);

        normalized.setUavCount(request.getUavCount());
        normalized.setHapCount(request.getHapCount());
        normalized.setGroundStationCount(request.getGroundStationCount());
        normalized.setTerminalCount(request.getTerminalCount());

        Double centerLng = request.getCenterLng();
        Double centerLat = request.getCenterLat();
        if ((centerLng == null || centerLat == null) && request.getScenarioId() != null) {
            Scenario scenario = scenarioService.get(request.getScenarioId());
            if (scenario != null) {
                if (centerLng == null) centerLng = scenario.getCenterLng();
                if (centerLat == null) centerLat = scenario.getCenterLat();
            }
        }
        normalized.setCenterLng(centerLng != null ? centerLng : ScenarioService.DEFAULT_CENTER_LNG);
        normalized.setCenterLat(centerLat != null ? centerLat : ScenarioService.DEFAULT_CENTER_LAT);

        normalized.setNodes(request.getNodes());

        return normalized;
    }

    private static boolean hasExplicitNodes(SimulationRequest request) {
        return request.getNodes() != null && !request.getNodes().isEmpty();
    }
}
