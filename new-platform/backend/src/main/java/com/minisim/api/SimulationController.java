package com.minisim.api;

import com.minisim.model.FrameData;
import com.minisim.model.SimulationRequest;
import com.minisim.model.SimulationState;
import com.minisim.service.SimulationService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/simulations")
public class SimulationController {
    private final SimulationService simulationService;

    public SimulationController(SimulationService simulationService) {
        this.simulationService = simulationService;
    }

    @PostMapping
    public SimulationState start(@RequestBody SimulationRequest request) {
        return simulationService.startSimulation(request);
    }

    @PostMapping("/{id}/pause")
    public ResponseEntity<SimulationState> pause(@PathVariable("id") String id) {
        return wrap(() -> simulationService.pauseSimulation(id));
    }

    @PostMapping("/{id}/resume")
    public ResponseEntity<SimulationState> resume(@PathVariable("id") String id) {
        return wrap(() -> simulationService.resumeSimulation(id));
    }

    @PostMapping("/{id}/stop")
    public ResponseEntity<SimulationState> stop(@PathVariable("id") String id) {
        return wrap(() -> simulationService.stopSimulation(id));
    }

    @GetMapping("/{id}/state")
    public ResponseEntity<SimulationState> state(@PathVariable("id") String id) {
        return wrap(() -> simulationService.getState(id));
    }

    @GetMapping("/{id}/frames/{slot}")
    public ResponseEntity<FrameData> frame(
            @PathVariable("id") String id,
            @PathVariable("slot") int slot
    ) {
        return wrap(() -> simulationService.getFrame(id, slot));
    }

    private <T> ResponseEntity<T> wrap(Provider<T> provider) {
        try {
            return ResponseEntity.ok(provider.get());
        } catch (IllegalArgumentException ex) {
            return ResponseEntity.notFound().build();
        }
    }

    private interface Provider<T> {
        T get();
    }
}
