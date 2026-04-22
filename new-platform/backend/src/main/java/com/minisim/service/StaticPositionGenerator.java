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
 * By default all slots reuse the same node positions, and an overload
 * can interpolate from a start layout to a target layout.
 * Links are auto-generated
 * (UAV ring + terminal-to-nearest-UAV + ground-station-to-UAV-0)
 * so the visualization still has a topology to draw.
 */
public class StaticPositionGenerator implements FrameGenerator {

    @Override
    public List<FrameData> generateFrames(SimulationRequest request) {
        List<NodeData> source = request.getNodes() != null ? request.getNodes() : new ArrayList<NodeData>();
        return generateFrames(request, source, source);
    }

    public List<FrameData> generateFrames(SimulationRequest request, List<NodeData> startNodes, List<NodeData> endNodes) {
        int totalSlots = Math.max(request.getTotalSlots(), 1);
        List<NodeData> safeStartNodes = startNodes != null ? startNodes : new ArrayList<NodeData>();
        List<NodeData> safeEndNodes = endNodes != null ? endNodes : safeStartNodes;

        List<NodeData> orderedStartNodes = cloneNodes(safeStartNodes);
        Map<String, NodeData> endById = indexById(safeEndNodes);
        Map<String, NodeData> startById = indexById(orderedStartNodes);
        for (NodeData end : safeEndNodes) {
            if (!startById.containsKey(end.getId())) {
                orderedStartNodes.add(cloneNode(end));
            }
        }

        List<NodeData> uavs = filterByType(safeEndNodes, NodeType.UAV);
        List<NodeData> terminals = filterByType(safeEndNodes, NodeType.TERMINAL);
        List<NodeData> groundStations = filterByType(safeEndNodes, NodeType.GROUND_STATION);

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
            double progress = totalSlots == 1 ? 1.0 : (double) slot / (double) (totalSlots - 1);
            double angle = 2.0 * Math.PI * slot / Math.max(totalSlots, 1);
            Map<String, Double> metrics = new HashMap<>();
            metrics.put("throughput", 100.0 + 20.0 * Math.sin(angle));
            metrics.put("latency", 40.0 + 10.0 * Math.cos(angle));

            frames.add(new FrameData(
                    slot,
                    interpolateNodes(orderedStartNodes, endById, progress),
                    new ArrayList<LinkData>(staticLinks),
                    metrics
            ));
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
            out.add(cloneNode(n));
        }
        return out;
    }

    private static NodeData cloneNode(NodeData src) {
        return new NodeData(src.getId(), src.getType(), src.getLng(), src.getLat(), src.getHeight(), src.getName());
    }

    private static Map<String, NodeData> indexById(List<NodeData> nodes) {
        Map<String, NodeData> out = new HashMap<>();
        for (NodeData n : nodes) {
            out.put(n.getId(), n);
        }
        return out;
    }

    private static List<NodeData> interpolateNodes(
            List<NodeData> startNodes,
            Map<String, NodeData> endById,
            double progress
    ) {
        List<NodeData> out = new ArrayList<>(startNodes.size());
        for (NodeData start : startNodes) {
            NodeData end = endById.get(start.getId());
            if (end == null) {
                end = start;
            }
            out.add(new NodeData(
                    start.getId(),
                    end.getType() != null ? end.getType() : start.getType(),
                    lerp(start.getLng(), end.getLng(), progress),
                    lerp(start.getLat(), end.getLat(), progress),
                    lerp(start.getHeight(), end.getHeight(), progress),
                    end.getName() != null ? end.getName() : start.getName()
            ));
        }
        return out;
    }

    private static double lerp(double from, double to, double progress) {
        return from + (to - from) * progress;
    }
}
