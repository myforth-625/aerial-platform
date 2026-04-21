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
 * Produces per-slot frames for a mixed-node aerial scenario.
 * Nodes are placed around a geographic center (lng/lat) and moved slot by slot:
 * UAV orbits at low altitude, HAP drifts on a larger, slower circle,
 * GROUND_STATION is stationary, TERMINAL jitters on the ground.
 */
public class CircleOrbitGenerator implements FrameGenerator {

    private static final double METERS_PER_DEG_LAT = 111320.0;

    @Override
    public List<FrameData> generateFrames(SimulationRequest request) {
        int totalSlots = Math.max(request.getTotalSlots(), 1);
        double radiusMeters = request.getAreaSize() > 0 ? request.getAreaSize() : 400.0;
        double speed = request.getSpeed() > 0 ? request.getSpeed() : 1.0;

        double centerLng = request.getCenterLng() != null ? request.getCenterLng() : 116.3544;
        double centerLat = request.getCenterLat() != null ? request.getCenterLat() : 39.9883;
        double metersPerDegLng = METERS_PER_DEG_LAT * Math.cos(Math.toRadians(centerLat));

        int uavCount = nonNullOr(request.getUavCount(), Math.max(request.getNodeCount() / 2, 4));
        int hapCount = nonNullOr(request.getHapCount(), 2);
        int gsCount = nonNullOr(request.getGroundStationCount(), 3);
        int terminalCount = nonNullOr(request.getTerminalCount(), Math.max(request.getNodeCount() / 2, 6));

        double[][] terminalOffsets = buildTerminalOffsets(terminalCount, radiusMeters);

        List<FrameData> frames = new ArrayList<>();
        for (int slot = 0; slot < totalSlots; slot++) {
            double slotAngle = 2.0 * Math.PI * slot / Math.max(totalSlots, 1) * speed;

            List<NodeData> nodes = new ArrayList<>();

            for (int i = 0; i < uavCount; i++) {
                double offset = 2.0 * Math.PI * i / uavCount;
                double angle = slotAngle + offset;
                double x = radiusMeters * Math.cos(angle);
                double y = radiusMeters * Math.sin(angle);
                nodes.add(toNode("UAV-" + i, NodeType.UAV,
                        centerLng, centerLat, metersPerDegLng,
                        x, y, 120.0));
            }

            for (int i = 0; i < hapCount; i++) {
                double offset = 2.0 * Math.PI * i / Math.max(hapCount, 1);
                double angle = slotAngle * 0.3 + offset;
                double x = radiusMeters * 1.8 * Math.cos(angle);
                double y = radiusMeters * 1.8 * Math.sin(angle);
                nodes.add(toNode("HAP-" + i, NodeType.HAP,
                        centerLng, centerLat, metersPerDegLng,
                        x, y, 500.0));
            }

            for (int i = 0; i < gsCount; i++) {
                double angle = 2.0 * Math.PI * i / Math.max(gsCount, 1);
                double x = radiusMeters * 0.5 * Math.cos(angle);
                double y = radiusMeters * 0.5 * Math.sin(angle);
                nodes.add(toNode("GS-" + i, NodeType.GROUND_STATION,
                        centerLng, centerLat, metersPerDegLng,
                        x, y, 0.0));
            }

            for (int i = 0; i < terminalCount; i++) {
                double jitterAngle = slotAngle + i;
                double jx = terminalOffsets[i][0] + 5.0 * Math.cos(jitterAngle);
                double jy = terminalOffsets[i][1] + 5.0 * Math.sin(jitterAngle);
                nodes.add(toNode("TERM-" + i, NodeType.TERMINAL,
                        centerLng, centerLat, metersPerDegLng,
                        jx, jy, 1.5));
            }

            List<LinkData> links = new ArrayList<>();
            // UAV ring
            for (int i = 0; i < uavCount; i++) {
                int next = (i + 1) % uavCount;
                links.add(new LinkData("L-UAV-" + i, "UAV-" + i, "UAV-" + next));
            }
            // Each terminal uplinks to its nearest-ish UAV (simple modulo mapping)
            if (uavCount > 0) {
                for (int i = 0; i < terminalCount; i++) {
                    links.add(new LinkData("L-UL-" + i, "TERM-" + i, "UAV-" + (i % uavCount)));
                }
            }
            // Each ground station connects to UAV-0 as a backhaul anchor
            if (uavCount > 0) {
                for (int i = 0; i < gsCount; i++) {
                    links.add(new LinkData("L-GS-" + i, "GS-" + i, "UAV-0"));
                }
            }

            Map<String, Double> metrics = new HashMap<>();
            metrics.put("throughput", 100.0 + 20.0 * Math.sin(slotAngle));
            metrics.put("latency", 40.0 + 10.0 * Math.cos(slotAngle));

            frames.add(new FrameData(slot, nodes, links, metrics));
        }

        return frames;
    }

    private static int nonNullOr(Integer v, int fallback) {
        return v != null && v > 0 ? v : fallback;
    }

    private static NodeData toNode(String id, NodeType type,
                                   double centerLng, double centerLat, double metersPerDegLng,
                                   double xMeters, double yMeters, double height) {
        double lat = centerLat + yMeters / METERS_PER_DEG_LAT;
        double lng = centerLng + xMeters / metersPerDegLng;
        return new NodeData(id, type, lng, lat, height);
    }

    private static double[][] buildTerminalOffsets(int count, double radiusMeters) {
        double[][] out = new double[count][2];
        // Deterministic pseudo-random distribution inside a disk of `radiusMeters`
        for (int i = 0; i < count; i++) {
            double r = radiusMeters * Math.sqrt(((i * 13 + 7) % 100) / 100.0);
            double theta = 2.0 * Math.PI * (((i * 37 + 11) % 100) / 100.0);
            out[i][0] = r * Math.cos(theta);
            out[i][1] = r * Math.sin(theta);
        }
        return out;
    }
}
