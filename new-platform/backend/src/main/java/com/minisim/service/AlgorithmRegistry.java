package com.minisim.service;

import com.minisim.model.AlgorithmOption;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

@Component
public class AlgorithmRegistry {
    private final Map<String, AlgorithmOption> options = new LinkedHashMap<>();
    private final Map<String, FrameGenerator> generators = new LinkedHashMap<>();

    public AlgorithmRegistry() {
        register(
                "circle-orbit",
                "Circle Orbit",
                "Nodes move on circular orbits for quick visualization",
                new CircleOrbitGenerator()
        );
    }

    private void register(String id, String name, String description, FrameGenerator generator) {
        options.put(id, new AlgorithmOption(id, name, description));
        generators.put(id, generator);
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
}
