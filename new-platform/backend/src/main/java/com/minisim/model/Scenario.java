package com.minisim.model;

public class Scenario {
    private String id;
    private String name;
    private String description;
    private double centerLng;
    private double centerLat;
    private long createdAt;

    public Scenario() {
    }

    public Scenario(String id, String name, String description,
                    double centerLng, double centerLat, long createdAt) {
        this.id = id;
        this.name = name;
        this.description = description;
        this.centerLng = centerLng;
        this.centerLat = centerLat;
        this.createdAt = createdAt;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public double getCenterLng() {
        return centerLng;
    }

    public void setCenterLng(double centerLng) {
        this.centerLng = centerLng;
    }

    public double getCenterLat() {
        return centerLat;
    }

    public void setCenterLat(double centerLat) {
        this.centerLat = centerLat;
    }

    public long getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(long createdAt) {
        this.createdAt = createdAt;
    }
}
