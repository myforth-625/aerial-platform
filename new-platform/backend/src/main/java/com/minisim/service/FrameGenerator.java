package com.minisim.service;

import com.minisim.model.FrameData;
import com.minisim.model.SimulationRequest;
import java.util.List;

public interface FrameGenerator {
    List<FrameData> generateFrames(SimulationRequest request);
}
