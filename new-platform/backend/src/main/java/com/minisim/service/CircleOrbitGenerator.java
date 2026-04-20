package com.minisim.service;

import com.minisim.model.FrameData;
import com.minisim.model.LinkData;
import com.minisim.model.NodeData;
import com.minisim.model.SimulationRequest;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class CircleOrbitGenerator implements FrameGenerator {
    @Override
    public List<FrameData> generateFrames(SimulationRequest request) {
        int totalSlots = Math.max(request.getTotalSlots(), 1);
        int nodeCount = Math.max(request.getNodeCount(), 1);
        double radius = request.getAreaSize() > 0 ? request.getAreaSize() : 120.0;
        double speed = request.getSpeed() > 0 ? request.getSpeed() : 1.0;

        List<FrameData> frames = new ArrayList<>();
        for (int slot = 0; slot < totalSlots; slot++) {
            double baseAngle = 2.0 * Math.PI * slot / totalSlots * speed;
            List<NodeData> nodes = new ArrayList<>();
            for (int i = 0; i < nodeCount; i++) {
                double offset = 2.0 * Math.PI * i / nodeCount;
                double angle = baseAngle + offset;
                double x = radius * Math.cos(angle);
                double y = radius * Math.sin(angle);
                double z = 20.0 + 10.0 * Math.sin(angle * 1.5);
                nodes.add(new NodeData("UAV-" + i, "UAV", x, y, z));
            }

            List<LinkData> links = new ArrayList<>();
            for (int i = 0; i < nodeCount; i++) {
                int next = (i + 1) % nodeCount;
                links.add(new LinkData("L-" + i, "UAV-" + i, "UAV-" + next));
            }

            Map<String, Double> metrics = new HashMap<>();
            metrics.put("throughput", 100.0 + 20.0 * Math.sin(baseAngle));
            metrics.put("latency", 40.0 + 10.0 * Math.cos(baseAngle));

            frames.add(new FrameData(slot, nodes, links, metrics));
        }

        return frames;
    }
}
