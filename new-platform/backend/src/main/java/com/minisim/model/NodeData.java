package com.minisim.model;

public class NodeData {
    private String id;
    private String type;
    private double x;
    private double y;
    private double z;

    public NodeData() {
    }

    public NodeData(String id, String type, double x, double y, double z) {
        this.id = id;
        this.type = type;
        this.x = x;
        this.y = y;
        this.z = z;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public double getX() {
        return x;
    }

    public void setX(double x) {
        this.x = x;
    }

    public double getY() {
        return y;
    }

    public void setY(double y) {
        this.y = y;
    }

    public double getZ() {
        return z;
    }

    public void setZ(double z) {
        this.z = z;
    }
}
