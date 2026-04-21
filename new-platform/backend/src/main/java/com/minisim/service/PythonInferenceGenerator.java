package com.minisim.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.minisim.config.InferenceProperties;
import com.minisim.model.FrameData;
import com.minisim.model.NodeData;
import com.minisim.model.NodeType;
import com.minisim.model.SimulationRequest;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.stream.Stream;

/**
 * Calls inference.py to redeploy UAV positions based on terminal distribution.
 *
 * Input: request.nodes must contain at least one UAV/HAP and one TERMINAL.
 * The generator writes aerialNode.json / terminalSnapshot.json to a temp
 * work directory, runs the Python script, reads aerialNodeResult.json,
 * rebuilds NodeData with updated coordinates, then delegates to
 * StaticPositionGenerator for frame/link composition.
 */
public class PythonInferenceGenerator implements FrameGenerator {

    private final InferenceProperties props;
    private final ObjectMapper objectMapper;
    private final String deploymentMode;
    private final StaticPositionGenerator staticFallback = new StaticPositionGenerator();

    public PythonInferenceGenerator(InferenceProperties props,
                                    ObjectMapper objectMapper,
                                    String deploymentMode) {
        this.props = props;
        this.objectMapper = objectMapper;
        this.deploymentMode = deploymentMode;
    }

    @Override
    public List<FrameData> generateFrames(SimulationRequest request) {
        List<NodeData> source = request.getNodes() != null ? request.getNodes() : new ArrayList<>();

        List<NodeData> aerial = new ArrayList<>();
        List<NodeData> terminals = new ArrayList<>();
        List<NodeData> others = new ArrayList<>();
        for (NodeData n : source) {
            if (n.getType() == NodeType.UAV || n.getType() == NodeType.HAP) {
                aerial.add(n);
            } else if (n.getType() == NodeType.TERMINAL) {
                terminals.add(n);
            } else {
                others.add(n);
            }
        }

        if (aerial.isEmpty()) {
            throw new IllegalArgumentException(
                    "MADDPG inference requires at least one UAV or HAP node. Please import or add UAV nodes.");
        }
        if (terminals.isEmpty()) {
            throw new IllegalArgumentException(
                    "MADDPG inference requires ground TERMINAL nodes for clustering. Please import or add terminal nodes.");
        }

        Path workDir = null;
        try {
            workDir = createWorkDir();
            writeAerialInput(workDir, aerial);
            writeTerminalInput(workDir, terminals);

            runPython(workDir);

            List<NodeData> updatedAerial = readAerialResult(workDir, aerial);
            List<NodeData> merged = new ArrayList<>(updatedAerial.size() + terminals.size() + others.size());
            merged.addAll(updatedAerial);
            merged.addAll(terminals);
            merged.addAll(others);

            SimulationRequest staticRequest = copyRequestWithNodes(request, merged);
            return staticFallback.generateFrames(staticRequest);
        } catch (IOException e) {
            throw new RuntimeException("Inference IO error: " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("Inference interrupted", e);
        } finally {
            if (workDir != null && !props.isKeepWorkDir()) {
                deleteRecursively(workDir);
            }
        }
    }

    private Path createWorkDir() throws IOException {
        Path root = Paths.get(props.getWorkDir()).toAbsolutePath();
        Files.createDirectories(root);
        Path dir = root.resolve(UUID.randomUUID().toString());
        Files.createDirectories(dir);
        return dir;
    }

    private void writeAerialInput(Path workDir, List<NodeData> aerial) throws IOException {
        List<Map<String, Object>> payload = new ArrayList<>(aerial.size());
        for (NodeData n : aerial) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("id", n.getId());
            item.put("type", n.getType() == NodeType.HAP ? "HAP" : "UAV");
            item.put("longitude", Double.toString(n.getLng()));
            item.put("latitude", Double.toString(n.getLat()));
            item.put("altitude", Double.toString(n.getHeight()));
            item.put("signalRadius", "210.0");
            item.put("maxGroundSignalAngle", "60.0");
            payload.add(item);
        }
        objectMapper.writerWithDefaultPrettyPrinter()
                .writeValue(workDir.resolve("aerialNode.json").toFile(), payload);
    }

    private void writeTerminalInput(Path workDir, List<NodeData> terminals) throws IOException {
        List<Map<String, Object>> payload = new ArrayList<>(terminals.size());
        for (NodeData n : terminals) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("id", n.getId());
            item.put("longitude", Double.toString(n.getLng()));
            item.put("latitude", Double.toString(n.getLat()));
            payload.add(item);
        }
        objectMapper.writerWithDefaultPrettyPrinter()
                .writeValue(workDir.resolve("terminalSnapshot.json").toFile(), payload);
    }

    private void runPython(Path workDir) throws IOException, InterruptedException {
        Path scriptDirAbs = Paths.get(props.getScriptDir()).toAbsolutePath().normalize();
        Path scriptPath = scriptDirAbs.resolve(props.getScriptName());
        if (!Files.exists(scriptPath)) {
            throw new RuntimeException("Python script not found: " + scriptPath);
        }
        Path modelPathAbs = scriptDirAbs.resolve(props.getModelPath()).normalize();

        List<String> cmd = Arrays.asList(
                props.getPythonCommand(),
                scriptPath.toString(),
                "--work_dir", workDir.toString(),
                "--input_nodes", "aerialNode.json",
                "--input_terminals", "terminalSnapshot.json",
                "--output_nodes", "aerialNodeResult.json",
                "--model_path", modelPathAbs.toString(),
                "--deployment_mode", deploymentMode
        );

        ProcessBuilder pb = new ProcessBuilder(cmd)
                .directory(scriptDirAbs.toFile())
                .redirectErrorStream(true);
        Process process = pb.start();

        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append('\n');
            }
        }

        boolean finished = process.waitFor(props.getTimeoutSeconds(), TimeUnit.SECONDS);
        if (!finished) {
            process.destroyForcibly();
            throw new RuntimeException("Python inference timed out after " + props.getTimeoutSeconds() + "s. Output tail:\n" + tail(output, 2000));
        }
        int exit = process.exitValue();
        if (exit != 0) {
            throw new RuntimeException("Python inference failed with exit " + exit + ". Output tail:\n" + tail(output, 2000));
        }
    }

    private List<NodeData> readAerialResult(Path workDir, List<NodeData> originalAerial) throws IOException {
        Path resultFile = workDir.resolve("aerialNodeResult.json");
        if (!Files.exists(resultFile)) {
            throw new RuntimeException("Python did not produce aerialNodeResult.json");
        }

        List<Map<String, Object>> parsed = objectMapper.readValue(
                resultFile.toFile(),
                objectMapper.getTypeFactory().constructCollectionType(List.class, Map.class)
        );

        Map<String, NodeData> byId = new HashMap<>();
        for (NodeData n : originalAerial) {
            byId.put(String.valueOf(n.getId()), n);
        }

        List<NodeData> out = new ArrayList<>(parsed.size());
        for (Map<String, Object> item : parsed) {
            String id = String.valueOf(item.get("id"));
            NodeData template = byId.get(id);
            double lng = parseDouble(item.get("longitude"));
            double lat = parseDouble(item.get("latitude"));
            double alt = parseDouble(item.get("altitude"));
            if (template != null) {
                out.add(new NodeData(template.getId(), template.getType(), lng, lat, alt, template.getName()));
            } else {
                NodeType type = "HAP".equalsIgnoreCase(String.valueOf(item.get("type"))) ? NodeType.HAP : NodeType.UAV;
                out.add(new NodeData(id, type, lng, lat, alt));
            }
        }
        return out;
    }

    private static SimulationRequest copyRequestWithNodes(SimulationRequest src, List<NodeData> nodes) {
        SimulationRequest copy = new SimulationRequest();
        copy.setScenarioId(src.getScenarioId());
        copy.setAlgorithmId(src.getAlgorithmId());
        copy.setTotalSlots(src.getTotalSlots());
        copy.setNodeCount(src.getNodeCount());
        copy.setAreaSize(src.getAreaSize());
        copy.setSpeed(src.getSpeed());
        copy.setUavCount(src.getUavCount());
        copy.setHapCount(src.getHapCount());
        copy.setGroundStationCount(src.getGroundStationCount());
        copy.setTerminalCount(src.getTerminalCount());
        copy.setCenterLng(src.getCenterLng());
        copy.setCenterLat(src.getCenterLat());
        copy.setNodes(nodes);
        return copy;
    }

    private static double parseDouble(Object v) {
        if (v == null) return 0.0;
        if (v instanceof Number) return ((Number) v).doubleValue();
        try {
            return Double.parseDouble(String.valueOf(v).trim());
        } catch (NumberFormatException e) {
            return 0.0;
        }
    }

    private static String tail(StringBuilder sb, int max) {
        int len = sb.length();
        if (len <= max) return sb.toString();
        return "..." + sb.substring(len - max);
    }

    private static void deleteRecursively(Path path) {
        if (!Files.exists(path)) return;
        try (Stream<Path> stream = Files.walk(path)) {
            stream.sorted(Comparator.reverseOrder())
                    .map(Path::toFile)
                    .forEach(File::delete);
        } catch (IOException ignored) {
            // best-effort cleanup
        }
    }
}
