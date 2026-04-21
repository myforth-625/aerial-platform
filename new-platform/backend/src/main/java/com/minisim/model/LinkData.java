package com.minisim.model;

public class LinkData {
    private String id;
    private String sourceId;
    private String targetId;

    public LinkData() {
    }

    public LinkData(String id, String sourceId, String targetId) {
        this.id = id;
        this.sourceId = sourceId;
        this.targetId = targetId;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getSourceId() {
        return sourceId;
    }

    public void setSourceId(String sourceId) {
        this.sourceId = sourceId;
    }

    public String getTargetId() {
        return targetId;
    }

    public void setTargetId(String targetId) {
        this.targetId = targetId;
    }
}
