package com.minisim.service;

import com.minisim.model.FrameData;
import com.minisim.model.SimulationRequest;
import com.minisim.model.SimulationState;
import java.util.List;

public class SimulationSession {
    private final SimulationState state;
    private final SimulationRequest request;
    private final List<FrameData> frames;

    public SimulationSession(SimulationState state, SimulationRequest request, List<FrameData> frames) {
        this.state = state;
        this.request = request;
        this.frames = frames;
    }

    public SimulationState getState() {
        return state;
    }

    public SimulationRequest getRequest() {
        return request;
    }

    public List<FrameData> getFrames() {
        return frames;
    }
}
