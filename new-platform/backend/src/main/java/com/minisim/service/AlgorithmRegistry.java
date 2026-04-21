package com.minisim.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.minisim.config.InferenceProperties;
import com.minisim.model.AlgorithmOption;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Component;

@Component
public class AlgorithmRegistry {
    private final Map<String, AlgorithmOption> options = new LinkedHashMap<>();
    private final Map<String, FrameGenerator> generators = new LinkedHashMap<>();
    private final Set<String> nodeConsumingIds = new HashSet<>();

    public AlgorithmRegistry(InferenceProperties inferenceProperties, ObjectMapper objectMapper) {
        register(
                "circle-orbit",
                "Circle Orbit",
                "Nodes move on circular orbits for quick visualization",
                new CircleOrbitGenerator(),
                false
        );
        register(
                "maddpg-kmeans",
                "MADDPG K-means Deployment",
                "Cluster terminals with K-means and place UAVs at cluster centers (Python inference)",
                new PythonInferenceGenerator(inferenceProperties, objectMapper, "kmeans"),
                true
        );
    }

    private void register(String id, String name, String description, FrameGenerator generator, boolean consumesNodes) {
        options.put(id, new AlgorithmOption(id, name, description));
        generators.put(id, generator);
        if (consumesNodes) {
            nodeConsumingIds.add(id);
        }
    }

    public List<AlgorithmOption> getOptions() {
        return new ArrayList<>(options.values());
    }

    public FrameGenerator getGenerator(String id) {
        if (id == null || !generators.containsKey(id)) {
            return generators.values().iterator().next();
        }
        return generators.get(id);
    }

    public boolean hasGenerator(String id) {
        return id != null && generators.containsKey(id);
    }

    public boolean consumesNodes(String id) {
        return id != null && nodeConsumingIds.contains(id);
    }
}
