package com.minisim.model;

import java.util.List;
import java.util.Map;

public class FrameData {
    private int slot;
    private List<NodeData> nodes;
    private List<LinkData> links;
    private Map<String, Double> metrics;

    public FrameData() {
    }

    public FrameData(int slot, List<NodeData> nodes, List<LinkData> links, Map<String, Double> metrics) {
        this.slot = slot;
        this.nodes = nodes;
        this.links = links;
        this.metrics = metrics;
    }

    public int getSlot() {
        return slot;
    }

    public void setSlot(int slot) {
        this.slot = slot;
    }

    public List<NodeData> getNodes() {
        return nodes;
    }

    public void setNodes(List<NodeData> nodes) {
        this.nodes = nodes;
    }

    public List<LinkData> getLinks() {
        return links;
    }

    public void setLinks(List<LinkData> links) {
        this.links = links;
    }

    public Map<String, Double> getMetrics() {
        return metrics;
    }

    public void setMetrics(Map<String, Double> metrics) {
        this.metrics = metrics;
    }
}
