package com.minisim.model;

import java.util.List;

public class SimulationRequest {
    private String scenarioId;
    private String algorithmId;
    private int totalSlots;
    private int nodeCount;
    private double areaSize;
    private double speed;
    private Integer uavCount;
    private Integer hapCount;
    private Integer groundStationCount;
    private Integer terminalCount;
    private Double centerLng;
    private Double centerLat;
    private List<NodeData> nodes;

    public SimulationRequest() {
    }

    public String getScenarioId() {
        return scenarioId;
    }

    public void setScenarioId(String scenarioId) {
        this.scenarioId = scenarioId;
    }

    public String getAlgorithmId() {
        return algorithmId;
    }

    public void setAlgorithmId(String algorithmId) {
        this.algorithmId = algorithmId;
    }

    public int getTotalSlots() {
        return totalSlots;
    }

    public void setTotalSlots(int totalSlots) {
        this.totalSlots = totalSlots;
    }

    public int getNodeCount() {
        return nodeCount;
    }

    public void setNodeCount(int nodeCount) {
        this.nodeCount = nodeCount;
    }

    public double getAreaSize() {
        return areaSize;
    }

    public void setAreaSize(double areaSize) {
        this.areaSize = areaSize;
    }

    public double getSpeed() {
        return speed;
    }

    public void setSpeed(double speed) {
        this.speed = speed;
    }

    public Integer getUavCount() {
        return uavCount;
    }

    public void setUavCount(Integer uavCount) {
        this.uavCount = uavCount;
    }

    public Integer getHapCount() {
        return hapCount;
    }

    public void setHapCount(Integer hapCount) {
        this.hapCount = hapCount;
    }

    public Integer getGroundStationCount() {
        return groundStationCount;
    }

    public void setGroundStationCount(Integer groundStationCount) {
        this.groundStationCount = groundStationCount;
    }

    public Integer getTerminalCount() {
        return terminalCount;
    }

    public void setTerminalCount(Integer terminalCount) {
        this.terminalCount = terminalCount;
    }

    public Double getCenterLng() {
        return centerLng;
    }

    public void setCenterLng(Double centerLng) {
        this.centerLng = centerLng;
    }

    public Double getCenterLat() {
        return centerLat;
    }

    public void setCenterLat(Double centerLat) {
        this.centerLat = centerLat;
    }

    public List<NodeData> getNodes() {
        return nodes;
    }

    public void setNodes(List<NodeData> nodes) {
        this.nodes = nodes;
    }
}
