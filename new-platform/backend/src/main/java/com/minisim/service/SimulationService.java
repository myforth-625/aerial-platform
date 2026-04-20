package com.minisim.service;

import com.minisim.model.FrameData;
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
    private final Map<String, SimulationSession> sessions = new ConcurrentHashMap<>();

    public SimulationService(AlgorithmRegistry algorithmRegistry) {
        this.algorithmRegistry = algorithmRegistry;
    }

    public SimulationState startSimulation(SimulationRequest request) {
        SimulationRequest normalized = normalizeRequest(request);
        List<FrameData> frames = algorithmRegistry.getGenerator(normalized.getAlgorithmId())
                .generateFrames(normalized);

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
        normalized.setAreaSize(request.getAreaSize() > 0 ? request.getAreaSize() : 120.0);
        normalized.setSpeed(request.getSpeed() > 0 ? request.getSpeed() : 1.0);
        return normalized;
    }
}
