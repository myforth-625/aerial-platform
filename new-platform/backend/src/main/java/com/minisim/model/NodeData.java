package com.minisim.model;

public class NodeData {
    private String id;
    private NodeType type;
    private double lng;
    private double lat;
    private double height;
    private String name;

    public NodeData() {
    }

    public NodeData(String id, NodeType type, double lng, double lat, double height) {
        this.id = id;
        this.type = type;
        this.lng = lng;
        this.lat = lat;
        this.height = height;
    }

    public NodeData(String id, NodeType type, double lng, double lat, double height, String name) {
        this(id, type, lng, lat, height);
        this.name = name;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public NodeType getType() {
        return type;
    }

    public void setType(NodeType type) {
        this.type = type;
    }

    public double getLng() {
        return lng;
    }

    public void setLng(double lng) {
        this.lng = lng;
    }

    public double getLat() {
        return lat;
    }

    public void setLat(double lat) {
        this.lat = lat;
    }

    public double getHeight() {
        return height;
    }

    public void setHeight(double height) {
        this.height = height;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }
}
