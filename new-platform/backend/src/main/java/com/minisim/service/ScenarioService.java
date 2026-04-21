package com.minisim.service;

import com.minisim.model.Scenario;
import com.minisim.model.ScenarioCreateRequest;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Service;

@Service
public class ScenarioService {
    public static final double DEFAULT_CENTER_LNG = 116.3544;
    public static final double DEFAULT_CENTER_LAT = 39.9883;

    private final Map<String, Scenario> scenarios = new ConcurrentHashMap<>();

    public ScenarioService() {
        String id = UUID.randomUUID().toString();
        scenarios.put(id, new Scenario(
                id,
                "Demo Scenario",
                "Seed scenario for testing",
                DEFAULT_CENTER_LNG,
                DEFAULT_CENTER_LAT,
                System.currentTimeMillis()
        ));
    }

    public List<Scenario> list() {
        return new ArrayList<>(scenarios.values());
    }

    public Scenario create(ScenarioCreateRequest request) {
        String id = UUID.randomUUID().toString();
        String name = request.getName() == null || request.getName().trim().isEmpty()
                ? "Scenario " + id.substring(0, 6)
                : request.getName().trim();
        String description = request.getDescription() == null ? "" : request.getDescription().trim();
        double centerLng = request.getCenterLng() != null ? request.getCenterLng() : DEFAULT_CENTER_LNG;
        double centerLat = request.getCenterLat() != null ? request.getCenterLat() : DEFAULT_CENTER_LAT;
        Scenario scenario = new Scenario(id, name, description, centerLng, centerLat, System.currentTimeMillis());
        scenarios.put(id, scenario);
        return scenario;
    }

    public Scenario get(String id) {
        return scenarios.get(id);
    }
}
