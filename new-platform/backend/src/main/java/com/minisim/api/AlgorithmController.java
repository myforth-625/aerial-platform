package com.minisim.api;

import com.minisim.model.AlgorithmOption;
import com.minisim.service.AlgorithmRegistry;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/algorithms")
public class AlgorithmController {
    private final AlgorithmRegistry algorithmRegistry;

    public AlgorithmController(AlgorithmRegistry algorithmRegistry) {
        this.algorithmRegistry = algorithmRegistry;
    }

    @GetMapping
    public List<AlgorithmOption> list() {
        return algorithmRegistry.getOptions();
    }
}
