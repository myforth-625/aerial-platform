package com.minisim.model;

public class ScenarioCreateRequest {
    private String name;
    private String description;

    public ScenarioCreateRequest() {
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
}
