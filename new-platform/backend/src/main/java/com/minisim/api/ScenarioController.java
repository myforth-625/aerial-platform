package com.minisim.api;

import com.minisim.model.Scenario;
import com.minisim.model.ScenarioCreateRequest;
import com.minisim.service.ScenarioService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/scenarios")
public class ScenarioController {
    private final ScenarioService scenarioService;

    public ScenarioController(ScenarioService scenarioService) {
        this.scenarioService = scenarioService;
    }

    @GetMapping
    public List<Scenario> list() {
        return scenarioService.list();
    }

    @PostMapping
    public Scenario create(@RequestBody ScenarioCreateRequest request) {
        return scenarioService.create(request);
    }
}
