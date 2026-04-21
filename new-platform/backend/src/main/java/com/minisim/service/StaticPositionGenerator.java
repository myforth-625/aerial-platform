package com.minisim.service;

import com.minisim.model.FrameData;
import com.minisim.model.LinkData;
import com.minisim.model.NodeData;
import com.minisim.model.NodeType;
import com.minisim.model.SimulationRequest;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Produces frames from an explicit, user-provided node list.
 * All slots reuse the same node positions; links are auto-generated
 * (UAV ring + terminal-to-nearest-UAV + ground-station-to-UAV-0)
 * so the visualization still has a topology to draw.
 */
public class StaticPositionGenerator implements FrameGenerator {

    @Override
    public List<FrameData> generateFrames(SimulationRequest request) {
        int totalSlots = Math.max(request.getTotalSlots(), 1);
        List<NodeData> source = request.getNodes() != null ? request.getNodes() : new ArrayList<>();

        List<NodeData> uavs = filterByType(source, NodeType.UAV);
        List<NodeData> terminals = filterByType(source, NodeType.TERMINAL);
        List<NodeData> groundStations = filterByType(source, NodeType.GROUND_STATION);

        List<LinkData> staticLinks = new ArrayList<>();
        for (int i = 0; i < uavs.size(); i++) {
            NodeData a = uavs.get(i);
            NodeData b = uavs.get((i + 1) % uavs.size());
            if (!a.getId().equals(b.getId())) {
                staticLinks.add(new LinkData("L-UAV-" + i, a.getId(), b.getId()));
            }
        }
        if (!uavs.isEmpty()) {
            for (int i = 0; i < terminals.size(); i++) {
                NodeData term = terminals.get(i);
                NodeData uav = uavs.get(i % uavs.size());
                staticLinks.add(new LinkData("L-UL-" + i, term.getId(), uav.getId()));
            }
            NodeData anchor = uavs.get(0);
            for (int i = 0; i < groundStations.size(); i++) {
                NodeData gs = groundStations.get(i);
                staticLinks.add(new LinkData("L-GS-" + i, gs.getId(), anchor.getId()));
            }
        }

        List<FrameData> frames = new ArrayList<>();
        for (int slot = 0; slot < totalSlots; slot++) {
            double angle = 2.0 * Math.PI * slot / Math.max(totalSlots, 1);
            Map<String, Double> metrics = new HashMap<>();
            metrics.put("throughput", 100.0 + 20.0 * Math.sin(angle));
            metrics.put("latency", 40.0 + 10.0 * Math.cos(angle));

            frames.add(new FrameData(slot, cloneNodes(source), new ArrayList<>(staticLinks), metrics));
        }
        return frames;
    }

    private static List<NodeData> filterByType(List<NodeData> nodes, NodeType type) {
        List<NodeData> out = new ArrayList<>();
        for (NodeData n : nodes) {
            if (n.getType() == type) out.add(n);
        }
        return out;
    }

    private static List<NodeData> cloneNodes(List<NodeData> src) {
        List<NodeData> out = new ArrayList<>(src.size());
        for (NodeData n : src) {
            out.add(new NodeData(n.getId(), n.getType(), n.getLng(), n.getLat(), n.getHeight(), n.getName()));
        }
        return out;
    }
}
